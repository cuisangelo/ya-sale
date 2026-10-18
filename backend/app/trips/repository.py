from datetime import datetime

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.trips.domain import PlannedHop


class RouteRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def cached(self, key: str, planned_after: datetime) -> list[PlannedHop] | None:
        async with self._pool.connection() as conn:
            row = await (
                await conn.execute("SELECT hops FROM routes WHERE key = %s AND planned_at > %s", (key, planned_after))
            ).fetchone()
        if row is None:
            return None
        return [PlannedHop(hop["origin"], hop["destination"], tuple(hop["modes"])) for hop in row[0]]

    async def store(self, key: str, chain: list[PlannedHop], planned_at: datetime) -> None:
        hops = [{"origin": hop.origin, "destination": hop.destination, "modes": list(hop.modes)} for hop in chain]
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO routes (key, hops, planned_at) VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET hops = EXCLUDED.hops, planned_at = EXCLUDED.planned_at
                """,
                (key, Jsonb(hops), planned_at),
            )
