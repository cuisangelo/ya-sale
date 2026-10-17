from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.legs.domain import LegData, LegKey, LegVersion, is_new_version

CONFIRMATION_SOURCE = "ya-sale:confirmation"

_VERSIONS_SQL = """
    SELECT v.id, v.data, v.source_url, v.fetched_at,
           (SELECT count(*) FROM confirmations c WHERE c.version_id = v.id) AS confirmations
    FROM leg_versions v
    WHERE v.leg_id = %s
    ORDER BY v.id
"""


class AlreadyConfirmed(Exception):
    pass


class LegNotFound(Exception):
    pass


def _to_json(data: LegData) -> dict:
    return {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(data).items()}


def _from_json(raw: dict) -> LegData:
    return LegData(
        departure_point=raw["departure_point"],
        operator=raw["operator"],
        price_min_pen=Decimal(raw["price_min_pen"]) if raw["price_min_pen"] is not None else None,
        price_max_pen=Decimal(raw["price_max_pen"]) if raw["price_max_pen"] is not None else None,
        duration_min=raw["duration_min"],
        schedule_note=raw["schedule_note"],
        purchase_url=raw["purchase_url"],
    )


def _version(row) -> LegVersion:
    return LegVersion(id=row[0], data=_from_json(row[1]), source_url=row[2], fetched_at=row[3], confirmations=row[4])


class LegRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def leg_id_of(self, key: LegKey) -> int:
        async with self._pool.connection() as conn:
            row = await (await conn.execute(
                """
                INSERT INTO legs (origin, destination, mode) VALUES (%s, %s, %s)
                ON CONFLICT (origin, destination, mode) DO UPDATE SET origin = EXCLUDED.origin
                RETURNING id
                """,
                (key.origin, key.destination, key.mode),
            )).fetchone()
        return row[0]

    async def _versions_by_id(self, leg_id: int) -> list[LegVersion]:
        async with self._pool.connection() as conn:
            rows = await (await conn.execute(_VERSIONS_SQL, (leg_id,))).fetchall()
        return [_version(row) for row in rows]

    async def versions(self, key: LegKey) -> list[LegVersion]:
        async with self._pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT id FROM legs WHERE origin = %s AND destination = %s AND mode = %s",
                (key.origin, key.destination, key.mode),
            )).fetchone()
        return [] if row is None else await self._versions_by_id(row[0])

    async def get(self, leg_id: int) -> tuple[LegKey, list[LegVersion]]:
        async with self._pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT origin, destination, mode FROM legs WHERE id = %s", (leg_id,)
            )).fetchone()
        if row is None:
            raise LegNotFound(leg_id)
        return LegKey(row[0], row[1], row[2]), await self._versions_by_id(leg_id)

    async def record_version(self, key: LegKey, data: LegData, source_url: str, fetched_at: datetime) -> LegVersion:
        leg_id = await self.leg_id_of(key)
        existing = await self._versions_by_id(leg_id)
        if existing and not is_new_version(existing[-1].data, data):
            newest = existing[-1]
            async with self._pool.connection() as conn:
                await conn.execute("UPDATE leg_versions SET fetched_at = %s WHERE id = %s", (fetched_at, newest.id))
            return LegVersion(newest.id, newest.data, newest.source_url, fetched_at, newest.confirmations)
        async with self._pool.connection() as conn:
            row = await (await conn.execute(
                "INSERT INTO leg_versions (leg_id, data, source_url, fetched_at) VALUES (%s, %s, %s, %s) RETURNING id",
                (leg_id, Jsonb(_to_json(data)), source_url, fetched_at),
            )).fetchone()
        return LegVersion(row[0], data, source_url, fetched_at, 0)

    async def _add_confirmation(self, version_id: int, fingerprint: str, display_name: str | None, kind: str) -> None:
        try:
            async with self._pool.connection() as conn:
                await conn.execute(
                    "INSERT INTO confirmations (version_id, fingerprint, display_name, kind) VALUES (%s, %s, %s, %s)",
                    (version_id, fingerprint, display_name, kind),
                )
        except UniqueViolation as exc:
            raise AlreadyConfirmed(version_id) from exc

    async def confirm(self, version_id: int, fingerprint: str, display_name: str | None) -> None:
        await self._add_confirmation(version_id, fingerprint, display_name, "confirmation")

    async def correct(self, leg_id: int, data: LegData, fingerprint: str, display_name: str | None) -> LegVersion:
        async with self._pool.connection() as conn:
            row = await (await conn.execute(
                "INSERT INTO leg_versions (leg_id, data, source_url, fetched_at) VALUES (%s, %s, %s, now()) "
                "RETURNING id, fetched_at",
                (leg_id, Jsonb(_to_json(data)), CONFIRMATION_SOURCE),
            )).fetchone()
        await self._add_confirmation(row[0], fingerprint, display_name, "correction")
        return LegVersion(row[0], data, CONFIRMATION_SOURCE, row[1], 1)
