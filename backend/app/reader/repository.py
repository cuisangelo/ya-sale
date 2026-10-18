from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.departures.domain import Departure
from app.departures.serialization import departure_json
from app.reader.domain import ANY_ROUTE, Query, Recipe, Step

# A worker that died mid-read leaves its claim behind; after this long another worker may take it.
STALE_CLAIM = "10 minutes"


def _recipe(row) -> Recipe:
    data = row[0]
    return Recipe(**{**data, "steps": tuple(Step(**step) for step in data["steps"])})


def _departure(data: dict) -> Departure:
    return Departure(
        operator=data["operator"],
        departs_at=datetime.fromisoformat(data["departs_at"]),
        arrives_at=datetime.fromisoformat(data["arrives_at"]) if data["arrives_at"] else None,
        price_pen=Decimal(data["price_pen"]) if data["price_pen"] is not None else None,
        seats_available=data["seats_available"],
        booking_url=data["booking_url"],
        seller=data["seller"],
    )


class RecipeRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def find(self, domain: str, query: Query) -> Recipe | None:
        """The route's own recipe wins over the operator-wide one, which wins over nothing."""
        async with self._pool.connection() as conn:
            row = await (
                await conn.execute(
                    "SELECT recipe FROM operator_recipes WHERE domain = %s AND route_key IN (%s, %s) "
                    "ORDER BY route_key = %s LIMIT 1",
                    (domain, query.route_key, ANY_ROUTE, ANY_ROUTE),
                )
            ).fetchone()
        return _recipe(row) if row else None

    async def save(self, recipe: Recipe, compliance_note: str) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO operator_recipes (domain, route_key, status, recipe, compliance_note) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (domain, route_key) DO UPDATE SET status = EXCLUDED.status, recipe = EXCLUDED.recipe,
                    compliance_note = EXCLUDED.compliance_note, discovered_at = now()
                """,
                (recipe.domain, recipe.route_key, recipe.status, Jsonb(asdict(recipe)), compliance_note),
            )

    async def forget(self, recipe: Recipe) -> None:
        async with self._pool.connection() as conn:
            await conn.execute("DELETE FROM operator_recipes WHERE domain = %s AND route_key = %s", (recipe.domain, recipe.route_key))


class ResultRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def fresh(self, domain: str, query: Query, read_after: datetime) -> tuple[Departure, ...] | None:
        async with self._pool.connection() as conn:
            row = await (
                await conn.execute(
                    "SELECT departures FROM reader_results WHERE domain = %s AND route_key = %s AND travel_date = %s AND read_at > %s",
                    (domain, query.route_key, query.travel_date, read_after),
                )
            ).fetchone()
        return tuple(_departure(d) for d in row[0]) if row else None

    async def store(self, domain: str, query: Query, departures: tuple[Departure, ...], read_at: datetime) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO reader_results (domain, route_key, travel_date, departures, read_at) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (domain, route_key, travel_date) DO UPDATE SET departures = EXCLUDED.departures, read_at = EXCLUDED.read_at
                """,
                (domain, query.route_key, query.travel_date, Jsonb([departure_json(d) for d in departures]), read_at),
            )


class RequestQueue:
    """A queue in Postgres: the API enqueues without waiting, the reader worker drains it."""

    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def enqueue(self, domain: str, query: Query) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "INSERT INTO reader_requests (domain, route_key, travel_date, origin, destination) VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (domain, query.route_key, query.travel_date, query.origin, query.destination),
            )

    async def claim(self) -> tuple[str, Query] | None:
        async with self._pool.connection() as conn:
            row = await (
                await conn.execute(
                    f"""
                    UPDATE reader_requests SET claimed_at = now()
                    WHERE (domain, route_key, travel_date) = (
                        SELECT domain, route_key, travel_date FROM reader_requests
                        WHERE claimed_at IS NULL OR claimed_at < now() - interval '{STALE_CLAIM}'
                        ORDER BY requested_at LIMIT 1 FOR UPDATE SKIP LOCKED
                    )
                    RETURNING domain, origin, destination, travel_date
                    """
                )
            ).fetchone()
        return (row[0], Query(row[1], row[2], row[3])) if row else None

    async def done(self, domain: str, query: Query) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "DELETE FROM reader_requests WHERE domain = %s AND route_key = %s AND travel_date = %s",
                (domain, query.route_key, query.travel_date),
            )
