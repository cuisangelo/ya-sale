from pathlib import Path

from psycopg_pool import AsyncConnectionPool

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


# Lambda runs one request per instance (up to 10 instances); a trip refreshes its hops in parallel,
# so 4 connections each keeps the total under the ~80 a db.t4g.micro accepts.
POOL_MAX_SIZE = 4


def create_pool(database_url: str) -> AsyncConnectionPool:
    return AsyncConnectionPool(database_url, min_size=1, max_size=POOL_MAX_SIZE, open=False)


async def bootstrap_schema(pool: AsyncConnectionPool) -> None:
    async with pool.connection() as conn:
        await conn.execute(SCHEMA_PATH.read_text())
