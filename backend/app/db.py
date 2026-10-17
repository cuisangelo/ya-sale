from pathlib import Path

from psycopg_pool import AsyncConnectionPool

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def create_pool(database_url: str) -> AsyncConnectionPool:
    return AsyncConnectionPool(database_url, min_size=1, max_size=10, open=False)


async def bootstrap_schema(pool: AsyncConnectionPool) -> None:
    async with pool.connection() as conn:
        await conn.execute(SCHEMA_PATH.read_text())
