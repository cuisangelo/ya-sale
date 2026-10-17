from datetime import UTC, datetime
from typing import Protocol

from app.legs.domain import normalize_place
from app.places.domain import Point
from app.places.repository import PlaceRepository


class Geocoder(Protocol):
    async def geocode(self, place: str) -> Point | None: ...


class PlaceLocator:
    """Finds a place on the map, asking the paid geocoder only for names it has never seen."""

    def __init__(self, repo: PlaceRepository, geocoder: Geocoder):
        self._repo = repo
        self._geocoder = geocoder

    async def locate(self, name: str) -> Point | None:
        key = normalize_place(name)
        cached = await self._repo.cached(key)
        if cached is not None:
            return cached.point
        point = await self._geocoder.geocode(name)
        await self._repo.store(key, point, datetime.now(UTC))
        return point
