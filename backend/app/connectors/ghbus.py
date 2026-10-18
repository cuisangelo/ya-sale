import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel

from app.departures.domain import LIMA, Departure
from app.legs.domain import Mode, normalize_place

SITE_URL = "https://sales.ghbus.com.pe"
_DISTRICT = re.compile(r"\s*\(.*\)$")


class GhBusSearchFailed(RuntimeError):
    pass


class _Office(BaseModel):
    codigo: int
    descripcion: str  # "TARAPOTO (MORALES)"


class _Trip(BaseModel):
    fechaViaje: str  # "20/10/2026"
    horaPartida: str  # "03:00PM"
    nomServicio: str
    precio_N1: Decimal
    precio_N2: Decimal
    asientosDisponibles: int


class _Search(BaseModel):
    datos: list[_Trip]
    success: bool
    message: str


class GhBusSource:
    """GH Bus's own sales site. Its search runs in the session its route-and-date page opens, so that page is the link."""

    seller = "ghbus.com.pe"
    mode: Mode = "bus"

    def __init__(self, new_session: Callable[[], httpx.AsyncClient]):
        self._new_session = new_session
        self._offices: dict[str, int] | None = None

    async def departures(self, origin: str, destination: str, travel_date: date) -> list[Departure]:
        async with self._new_session() as session:
            if self._offices is None:
                self._offices = await _fetch_offices(session)
            origin_code = self._offices.get(normalize_place(origin))
            destination_code = self._offices.get(normalize_place(destination))
            if origin_code is None or destination_code is None:
                return []
            day = travel_date.strftime("%d/%m/%Y")
            day_page = f"{SITE_URL}/?idorigen={origin_code}&iddestino={destination_code}&fechaida={day}"
            (await session.get(day_page)).raise_for_status()
            body = {"CodiOrigen": origin_code, "CodiDestino": destination_code, "FechaViaje": day, "SoloProgramados": False}
            response = await session.post(f"{SITE_URL}/busqueda-turnos", json=body)
            response.raise_for_status()
        search = _Search.model_validate(response.json())
        if not search.success:
            raise GhBusSearchFailed(search.message)
        return [self._departure(trip, day_page) for trip in search.datos if trip.fechaViaje == day]

    def _departure(self, trip: _Trip, day_page: str) -> Departure:
        # A floor priced at 0 is sold out or missing on that bus, not free.
        prices = [p for p in (trip.precio_N1, trip.precio_N2) if p > 0]
        return Departure(
            operator=f"GH Bus · {trip.nomServicio}",
            departs_at=datetime.strptime(f"{trip.fechaViaje} {trip.horaPartida}", "%d/%m/%Y %I:%M%p").replace(tzinfo=LIMA),
            # Their arrival repeats the departure clock with a 00:00 duration, so it says nothing.
            arrives_at=None,
            price_pen=min(prices, default=None),
            seats_available=trip.asientosDisponibles,
            booking_url=day_page,
            seller=self.seller,
        )


async def _fetch_offices(session: httpx.AsyncClient) -> dict[str, int]:
    response = await session.get(f"{SITE_URL}/api/base/lista-oficinas")
    response.raise_for_status()
    offices = [_Office.model_validate(o) for o in response.json()["datos"]]
    return {normalize_place(_DISTRICT.sub("", o.descripcion)): o.codigo for o in offices}
