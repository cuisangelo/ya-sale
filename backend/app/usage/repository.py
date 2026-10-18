from psycopg_pool import AsyncConnectionPool

RECENT_LIMIT = 10
RECENT_TRIPS_LIMIT = 8

_SUMMARY_SQL = """
    SELECT
        (SELECT count(*) FROM trips WHERE fingerprint <> ALL(%(team)s)),
        (SELECT count(DISTINCT lower(destination)) FROM trips WHERE fingerprint <> ALL(%(team)s)),
        (SELECT count(DISTINCT fingerprint) FROM (
            SELECT fingerprint FROM trips UNION SELECT fingerprint FROM confirmations
         ) people WHERE fingerprint <> ALL(%(team)s)),
        (SELECT count(DISTINCT v.leg_id) FROM confirmations c JOIN leg_versions v ON v.id = c.version_id
         WHERE c.fingerprint <> ALL(%(team)s))
"""

_RECENT_SQL = """
    SELECT c.kind, c.display_name, l.mode, l.origin, l.destination, c.created_at
    FROM confirmations c
    JOIN leg_versions v ON v.id = c.version_id
    JOIN legs l ON l.id = v.leg_id
    WHERE c.fingerprint <> ALL(%(team)s)
    ORDER BY c.created_at DESC
    LIMIT %(limit)s
"""

_RECENT_TRIPS_SQL = """
    SELECT origin, destination, resolved_destination, created_at, destination_lat, destination_lng FROM (
        SELECT DISTINCT ON (lower(origin), lower(destination)) *
        FROM trips
        WHERE fingerprint <> ALL(%(team)s) AND resolved_destination IS NOT NULL
        ORDER BY lower(origin), lower(destination), created_at DESC
    ) latest
    ORDER BY created_at DESC
    LIMIT %(limit)s
"""


class UsageRepository:
    def __init__(self, pool: AsyncConnectionPool, team_fingerprints: frozenset[str]):
        self._pool = pool
        self._team = list(team_fingerprints)

    async def record_trip(self, origin: str, destination: str, fingerprint: str) -> int:
        async with self._pool.connection() as conn:
            row = await (await conn.execute(
                "INSERT INTO trips (origin, destination, fingerprint) VALUES (%s, %s, %s) RETURNING id",
                (origin, destination, fingerprint),
            )).fetchone()
        return row[0]

    async def resolve_trip(self, trip_id: int, place: str, lat: float, lng: float) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "UPDATE trips SET resolved_destination = %s, destination_lat = %s, destination_lng = %s WHERE id = %s",
                (place, lat, lng, trip_id),
            )

    async def recent_trips(self) -> list[dict]:
        async with self._pool.connection() as conn:
            rows = await (await conn.execute(_RECENT_TRIPS_SQL, {"team": self._team, "limit": RECENT_TRIPS_LIMIT})).fetchall()
        return [
            {"origin": origin, "destination": destination, "place": place, "at": at.isoformat(), "lat": lat, "lng": lng}
            for origin, destination, place, at, lat, lng in rows
        ]

    async def summary(self) -> dict:
        params = {"team": self._team, "limit": RECENT_LIMIT}
        async with self._pool.connection() as conn:
            trips, destinations, people, confirmed_legs = await (await conn.execute(_SUMMARY_SQL, params)).fetchone()
            recent = await (await conn.execute(_RECENT_SQL, params)).fetchall()
        return {
            "trips": trips,
            "destinations": destinations,
            "people": people,
            "confirmed_legs": confirmed_legs,
            "recent": [
                {"kind": kind, "display_name": name, "mode": mode, "origin": origin, "destination": destination, "at": at.isoformat()}
                for kind, name, mode, origin, destination, at in recent
            ],
        }
