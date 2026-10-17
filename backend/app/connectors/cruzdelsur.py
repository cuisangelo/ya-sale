import asyncio
from datetime import date, datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel

from app.departures.domain import LIMA, Departure
from app.legs.domain import normalize_place

API_URL = "https://one-api.cruzdelsur.com.pe/api/v2"
SITE_URL = "https://viajes.cruzdelsur.com.pe"
# Their API only answers requests that come from their booking site.
SITE_HEADERS = {"Origin": SITE_URL, "Referer": f"{SITE_URL}/"}
MAX_POLLS = 10


class SearchUnfinished(RuntimeError):
    pass


class _Pricing(BaseModel):
    total: Decimal


class _Trip(BaseModel):
    id: str
    departure: datetime
    arrival: datetime | None
    pricing: _Pricing
    availability: int | None
    line_id: str
    travel_agency: str
    is_buyable: bool


class _Line(BaseModel):
    name: str


class _SearchResult(BaseModel):
    state: str
    trips: list[_Trip]
    lines: dict[str, _Line]


class _Place(BaseModel):
    slug: str
    display: str
    city_name: str


class CruzDelSurSource:
    """Cruz del Sur's own booking API: every departure links to its seat page, which opens without a session."""

    seller = "cruzdelsur.com.pe"

    def __init__(self, client: httpx.AsyncClient, poll_interval_s: float):
        self._client = client
        self._poll_interval_s = poll_interval_s
        self._auth: dict[str, str] | None = None
        self._slugs: dict[str, str] | None = None

    async def departures(self, origin: str, destination: str, travel_date: date) -> list[Departure]:
        if self._auth is None or self._slugs is None:
            self._auth, self._slugs = await asyncio.gather(self._fetch_auth(), self._fetch_slugs())
        origin_slug = self._slugs.get(normalize_place(origin))
        destination_slug = self._slugs.get(normalize_place(destination))
        if origin_slug is None or destination_slug is None:
            return []
        result = await self._search(origin_slug, destination_slug, travel_date)
        return [
            self._departure(trip, result.lines)
            for trip in result.trips
            if trip.is_buyable and trip.departure.date() == travel_date
        ]

    async def _fetch_auth(self) -> dict[str, str]:
        # The public key their own web app reads at startup; it can rotate, so it is never stored.
        body = await self._get("/config")
        return {"Authorization": f"Token token={body['config']['environment_variables']['api']['desktopKey']}"}

    async def _fetch_slugs(self) -> dict[str, str]:
        places = [_Place.model_validate(p) for p in await self._get("/places")]
        return {normalize_place(name): p.slug for p in places for name in (p.display, p.city_name)}

    async def _search(self, origin: str, destination: str, travel_date: date) -> _SearchResult:
        body = {
            "origin": origin,
            "destination": destination,
            "date": travel_date.strftime("%d-%m-%Y"),
            "passengers": ["adult"],
            "way": "departure",
            "round": False,
        }
        response = await self._client.post(f"{API_URL}/search", json=body, headers=SITE_HEADERS | self._auth)
        response.raise_for_status()
        search_id = response.json()["search"]["id"]
        for _ in range(MAX_POLLS):
            result = _SearchResult.model_validate(await self._get(f"/search/{search_id}", params={"type": "bus"}))
            if result.state == "finished":
                return result
            await asyncio.sleep(self._poll_interval_s)
        raise SearchUnfinished(f"search {search_id} still {result.state} after {MAX_POLLS} polls")

    async def _get(self, path: str, params: dict | None = None):
        headers = SITE_HEADERS | (self._auth or {})
        response = await self._client.get(f"{API_URL}{path}", params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    def _departure(self, trip: _Trip, lines: dict[str, _Line]) -> Departure:
        line = lines.get(trip.line_id)
        return Departure(
            operator=f"{trip.travel_agency} · {line.name}" if line else trip.travel_agency,
            departs_at=trip.departure.replace(tzinfo=LIMA),
            arrives_at=trip.arrival.replace(tzinfo=LIMA) if trip.arrival else None,
            price_pen=trip.pricing.total,
            seats_available=trip.availability,
            # A link to the trip, not to a cart: opening it creates a fresh cart on their side every time.
            booking_url=f"{SITE_URL}/purchase/{trip.id}/new/A1",
            seller=self.seller,
        )
