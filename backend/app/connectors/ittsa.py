import json
import re
from datetime import date, datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel

from app.departures.domain import LIMA, Departure
from app.legs.domain import Mode, normalize_place

SITE_URL = "https://www.ittsabus.com/online"
ROUTES_URL = f"{SITE_URL}/"
# Their Next.js pages stream their data as JSON string chunks inside these script calls.
_FLIGHT_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
_TERMINAL = re.compile(r"\s*\(.*\)$")


class IttsaPageChanged(RuntimeError):
    pass


class _Route(BaseModel):
    idAgenciaOrigen: int
    agenciaOrigen: str  # "LIMA (LA VICTORIA)"
    idAgenciaDestino: int
    agenciaDestino: str


class _Trip(BaseModel):
    feSalidaPlanificada: datetime  # "2026-10-22 20:00:00"
    feLlegadaPlanificada: datetime
    claseServicio: str
    precioMinimoPiso1: Decimal
    precioMinimoPiso2: Decimal
    nuDisponibleP1: int
    nuDisponibleP2: int


class IttsaSource:
    """ITTSA's own sales site, which renders a route's trips for a day on a page that opens for any visitor."""

    seller = "ittsabus.com"
    mode: Mode = "bus"

    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        self._routes: dict[tuple[str, str], tuple[int, int]] | None = None

    async def departures(self, origin: str, destination: str, travel_date: date) -> list[Departure]:
        if self._routes is None:
            self._routes = await self._fetch_routes()
        route = self._routes.get((normalize_place(origin), normalize_place(destination)))
        if route is None:
            return []
        origin_id, destination_id = route
        day_page = (
            f"{SITE_URL}/programacion/?origenId={origin_id}&destinoId={destination_id}"
            f"&fechaIda={travel_date.isoformat()}&trip=oneway"
        )
        trips = [_Trip.model_validate(t) for t in (await self._page_data(day_page, "itinerarioIda"))["itinerarioIda"]]
        return [self._departure(trip, day_page) for trip in trips if trip.feSalidaPlanificada.date() == travel_date]

    async def _fetch_routes(self) -> dict[tuple[str, str], tuple[int, int]]:
        routes: dict[tuple[str, str], tuple[int, int]] = {}
        for route in map(_Route.model_validate, (await self._page_data(ROUTES_URL, "destinos"))["destinos"]):
            # Lima and Trujillo have two terminals each; their list is alphabetical, so a city keeps its first.
            key = (_city(route.agenciaOrigen), _city(route.agenciaDestino))
            routes.setdefault(key, (route.idAgenciaOrigen, route.idAgenciaDestino))
        return routes

    async def _page_data(self, url: str, key: str) -> dict:
        response = await self._client.get(url)
        response.raise_for_status()
        payload = "".join(json.loads(f'"{chunk}"') for chunk in _FLIGHT_CHUNK.findall(response.text))
        start = payload.find(f'{{"{key}"')
        if start == -1:
            raise IttsaPageChanged(f"no {key} in {url}")
        data, _ = json.JSONDecoder().raw_decode(payload, start)
        return data

    def _departure(self, trip: _Trip, day_page: str) -> Departure:
        return Departure(
            operator=f"ITTSA · {trip.claseServicio}",
            departs_at=trip.feSalidaPlanificada.replace(tzinfo=LIMA),
            arrives_at=trip.feLlegadaPlanificada.replace(tzinfo=LIMA),
            price_pen=min(trip.precioMinimoPiso1, trip.precioMinimoPiso2),
            seats_available=trip.nuDisponibleP1 + trip.nuDisponibleP2,
            booking_url=day_page,
            seller=self.seller,
        )


def _city(terminal: str) -> str:
    return normalize_place(_TERMINAL.sub("", terminal))
