import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import httpx

from app.departures.domain import LIMA, Departure
from app.legs.domain import Mode, normalize_place

SITE_URL = "https://www.linea.pe"
_TRIP_BLOCK = re.compile(r'id="pnlItinerario\d+"')
_DEPARTS = re.compile(r"<h2[^>]*>\s*(\d{1,2}:\d{2} [ap]m)\s*</h2>")
_SERVICE = re.compile(r'<h5 class="text-uppercase fs_servicio[^>]*>\s*([^<]+?)\s*</h5>')
_PRICE = re.compile(r"S/ (\d+(?:\.\d+)?)</b>")
_FREE_SEATS = re.compile(r"(\d+) libres</h5>")
_NO_TRIPS = "No se encontró itinerarios"


class LineaPageChanged(RuntimeError):
    pass


class LineaSource:
    """Línea's own booking site. Its trip list lives in the visitor's session, so rows can only link to its home."""

    seller = "linea.pe"
    mode: Mode = "bus"

    def __init__(self, new_session: Callable[[], httpx.AsyncClient]):
        self._new_session = new_session
        self._origins: dict[str, str] | None = None

    async def departures(self, origin: str, destination: str, travel_date: date) -> list[Departure]:
        # Their server keeps the first route a session searched, so every search needs a session of its own.
        async with self._new_session() as session:
            if self._origins is None:
                self._origins = _terminal_codes(await _call(session, "ListarOrigen", {}))
            origin_code = self._origins.get(normalize_place(origin))
            if origin_code is None:
                return []
            destinations = _terminal_codes(await _call(session, "ListarDestino", {"objOrigen": {"Origen": origin_code}}))
            destination_code = destinations.get(normalize_place(destination))
            if destination_code is None:
                return []
            day = travel_date.strftime("%d/%m/%Y")
            cart = {"Origen": origin_code, "Destino": destination_code, "FechaIda": day, "FechaVuelta": "", "chkPuntos": 0}
            await _call(session, "MostrarItinerario", {"Carrito": cart})
            response = await session.get(
                f"{SITE_URL}/ECommerce/wf_ListaItinerarios.aspx",
                params={"fechaIda": day, "fechaVuelta": "", "retorno": "false"},
            )
            response.raise_for_status()
        return [self._departure(block, travel_date) for block in _trip_blocks(response.text)]

    def _departure(self, block: str, travel_date: date) -> Departure:
        departs = _DEPARTS.search(block)
        service = _SERVICE.search(block)
        prices = _PRICE.findall(block)
        if departs is None or service is None or not prices:
            raise LineaPageChanged("a trip on their list has no departure time, service or price")
        clock = datetime.strptime(departs.group(1), "%I:%M %p").time()
        return Departure(
            operator=f"Línea · {service.group(1)}",
            departs_at=datetime.combine(travel_date, clock, tzinfo=LIMA),
            arrives_at=None,
            price_pen=min(map(Decimal, prices)),
            seats_available=sum(map(int, _FREE_SEATS.findall(block))),
            booking_url=f"{SITE_URL}/",
            seller=self.seller,
        )


async def _call(session: httpx.AsyncClient, method: str, body: dict):
    response = await session.post(f"{SITE_URL}/index.aspx/{method}", json=body)
    response.raise_for_status()
    return response.json()["d"]


def _terminal_codes(terminals: list[dict]) -> dict[str, str]:
    # A city's first terminal on their list is its main one ("Lima-Terminal Paseo La República" before "Plaza Norte").
    codes: dict[str, str] = {}
    for terminal in terminals:
        codes.setdefault(normalize_place(terminal["Mostrar"].split("-")[0]), terminal["Origen"])
    return codes


def _trip_blocks(page: str) -> list[str]:
    blocks = _TRIP_BLOCK.split(page)[1:]
    if not blocks and _NO_TRIPS not in page:
        raise LineaPageChanged("their trip list has neither trips nor its no-trips notice")
    return blocks
