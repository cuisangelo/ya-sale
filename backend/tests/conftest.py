import os

import httpx
import pytest

from app.config import load_settings
from app.db import bootstrap_schema, create_pool
from app.main import create_app

TEST_ENV = {
    "ANTHROPIC_API_KEY": "test",
    "TAVILY_API_KEY": "test",
    "EXA_API_KEY": "test",
    "DATABASE_URL": os.environ["DATABASE_URL"],
    "FINGERPRINT_SALT": "test-salt",
    "TEAM_FINGERPRINTS": "team-fp",
    "GOOGLE_MAPS_API_KEY": "test",
}


@pytest.fixture(scope="session")
def settings():
    return load_settings(TEST_ENV)


@pytest.fixture(scope="session")
async def _session_pool(settings):
    pool = create_pool(settings.database_url)
    await pool.open()
    await bootstrap_schema(pool)
    yield pool
    await pool.close()


@pytest.fixture
async def pool(_session_pool):
    async with _session_pool.connection() as conn:
        await conn.execute("TRUNCATE legs, leg_versions, confirmations, trips, places, rate_events, routes RESTART IDENTITY CASCADE")
    return _session_pool


@pytest.fixture
async def client(settings):
    app = create_app(settings)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
