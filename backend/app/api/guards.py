import hashlib

from psycopg_pool import AsyncConnectionPool
from starlette.requests import Request

WINDOW_SECONDS = 60.0


def fingerprint(request: Request, salt: str) -> str:
    """Anonymous, salted identity of a visitor; the raw IP never leaves this function."""
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "")
    agent = request.headers.get("user-agent", "")
    return hashlib.sha256(f"{salt}|{ip}|{agent}".encode()).hexdigest()[:16]


def same_origin(request: Request, public_origin: str) -> bool:
    """CSRF guard for cookie-authenticated writes: only the site's own pages may send them."""
    if request.headers.get("origin") != public_origin:
        return False
    # Browsers that send Fetch Metadata also say so directly; older ones are covered by Origin.
    return request.headers.get("sec-fetch-site", "same-origin") == "same-origin"


class RateLimiter:
    """Sliding window kept in Postgres, so it holds however many instances serve the API."""

    def __init__(self, pool: AsyncConnectionPool, per_minute: int):
        self._pool = pool
        self._per_minute = per_minute

    async def allow(self, key: str) -> bool:
        async with self._pool.connection() as conn, conn.transaction():
            # Serializes one visitor's requests so a burst cannot all read the same count.
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (key,))
            await conn.execute(
                "DELETE FROM rate_events WHERE fingerprint = %s AND created_at <= now() - make_interval(secs => %s)",
                (key, WINDOW_SECONDS),
            )
            row = await (await conn.execute("SELECT count(*) FROM rate_events WHERE fingerprint = %s", (key,))).fetchone()
            if row[0] >= self._per_minute:
                return False
            await conn.execute("INSERT INTO rate_events (fingerprint) VALUES (%s)", (key,))
            return True
