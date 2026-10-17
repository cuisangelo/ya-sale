import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

import httpx
from pydantic import BaseModel

from app.departures.domain import LIMA, Departure
from app.legs.domain import Mode, normalize_place

CITIES_URL = "https://api.oltursa.com.pe/ws-tienda/api/v1/cities"
SITE_URL = "https://www.oltursa.pe"
_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


class OltursaPageChanged(RuntimeError):
    pass


class _City(BaseModel):
    name: str
    slug: str


class _Trip(BaseModel):
    fecha_salida: str  # "2026-10-22 22:00:00.0"
    fllegada_programada: str  # "23/10"
    hllegada_programada: str  # "09:15"
    dgcategoria_servicio: str
    nasiento_disp: int
    nprecio_desde: Decimal


class OltursaSource:
    """Oltursa's public day page, which carries every trip of the day; its seat page has no URL, so rows link to that day."""

    seller = "oltursa.pe"
    mode: Mode = "bus"

    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        self._slugs: dict[str, str] | None = None

    async def departures(self, origin: str, destination: str, travel_date: date) -> list[Departure]:
        if self._slugs is None:
            self._slugs = await self._fetch_slugs()
        origin_slug = self._slugs.get(normalize_place(origin))
        destination_slug = self._slugs.get(normalize_place(destination))
        if origin_slug is None or destination_slug is None:
            return []
        day_page = f"{SITE_URL}/es/viajes/{origin_slug}/{destination_slug}/{travel_date.isoformat()}"
        departures = [self._departure(trip, day_page) for trip in await self._trips(day_page)]
        return [d for d in departures if d.departs_at.date() == travel_date]

    async def _fetch_slugs(self) -> dict[str, str]:
        response = await self._client.get(CITIES_URL)
        response.raise_for_status()
        return {normalize_place(city.name): city.slug for city in map(_City.model_validate, response.json())}

    async def _trips(self, day_page: str) -> list[_Trip]:
        response = await self._client.get(day_page)
        response.raise_for_status()
        match = _NEXT_DATA.search(response.text)
        if match is None:
            raise OltursaPageChanged(f"no __NEXT_DATA__ in {day_page}")
        trips = json.loads(match.group(1))["props"]["pageProps"]["routeInfo"]["outboundTrips"]
        return [_Trip.model_validate(trip) for trip in trips]

    def _departure(self, trip: _Trip, day_page: str) -> Departure:
        departs_at = datetime.strptime(trip.fecha_salida, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=LIMA)
        return Departure(
            operator=f"Oltursa · {trip.dgcategoria_servicio}",
            departs_at=departs_at,
            arrives_at=_arrival(departs_at, trip.fllegada_programada, trip.hllegada_programada),
            price_pen=trip.nprecio_desde,
            seats_available=trip.nasiento_disp,
            booking_url=day_page,
            seller=self.seller,
        )


def _arrival(departs_at: datetime, day_month: str, clock: str) -> datetime:
    # The page gives the arrival as "dd/mm" with no year; a trip that crosses New Year lands in the next one.
    arrives_at = datetime.strptime(f"{day_month}/{departs_at.year} {clock}", "%d/%m/%Y %H:%M").replace(tzinfo=LIMA)
    return arrives_at if arrives_at >= departs_at else arrives_at.replace(year=departs_at.year + 1)
