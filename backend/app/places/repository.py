from dataclasses import dataclass
from datetime import datetime

from psycopg_pool import AsyncConnectionPool

from app.places.domain import Point


@dataclass(frozen=True)
class CachedPlace:
    point: Point | None  # None: the geocoder had no exact match, so it is not asked again


class PlaceRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def cached(self, key: str) -> CachedPlace | None:
        async with self._pool.connection() as conn:
            row = await (await conn.execute("SELECT lat, lng FROM places WHERE key = %s", (key,))).fetchone()
        if row is None:
            return None
        return CachedPlace(None if row[0] is None else Point(row[0], row[1]))

    async def store(self, key: str, point: Point | None, fetched_at: datetime) -> None:
        lat, lng = (None, None) if point is None else (point.lat, point.lng)
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO places (key, lat, lng, fetched_at) VALUES (%s, %s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET lat = EXCLUDED.lat, lng = EXCLUDED.lng, fetched_at = EXCLUDED.fetched_at
                """,
                (key, lat, lng, fetched_at),
            )
