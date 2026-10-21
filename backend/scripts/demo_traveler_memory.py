"""Local demo: real app, disposable PostgreSQL, synthetic departures and HTTP memory fixture.

Run from backend with DATABASE_URL pointing at a disposable demo database:
PYTHONPATH=.:tests python scripts/demo_traveler_memory.py
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import uvicorn
from fake_atomicmemory import API_KEY, FakeAtomicMemory, build_fake_app

from app.api.guards import RateLimiter
from app.config import load_settings
from app.connectors.atomicmemory import AtomicMemoryPreferenceStore, atomicmemory_client
from app.db import bootstrap_schema, create_pool
from app.departures.domain import LIMA, Departure
from app.legs.domain import LegData, LegKey
from app.legs.repository import LegRepository
from app.main import Services, create_app
from app.trips.domain import PlannedHop
from app.trips.events import TripStarted, LegRefreshed, LegDepartures, TripDone
from app.usage.repository import UsageRepository
import os


class FixturePlanner:
    def __init__(self, legs):
        self.legs = legs

    async def plan(self, origin, destination, date, trip_id):
        yield TripStarted(trip_id, origin, destination, 1, (PlannedHop(origin, destination, ("bus",)),))
        key = LegKey.of(origin, destination, "bus")
        data = LegData("Terminal de ejemplo", None, Decimal(60), Decimal(95), 540, None, None)
        version = await self.legs.record_version(key, data, "https://example.com/demo", datetime.now(UTC))
        yield LegRefreshed(0, await self.legs.leg_id_of(key), "bus", origin, destination, "extracted", version, ())
        departures = tuple(Departure(name, datetime.fromisoformat(f"{date}T{time}:00").replace(tzinfo=LIMA),
                                    None, Decimal(price), 12, "https://example.com/demo", "example.com")
                           for name, time, price in (("Empresa de ejemplo A", "08:30", "70"),
                                                     ("Empresa de ejemplo B", "21:00", "95"),
                                                     ("Empresa de ejemplo C", "22:30", "60")))
        yield LegDepartures(0, "bus", departures)
        yield TripDone(1)


async def main():
    env = {name: "demo-only" for name in ("ANTHROPIC_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY", "FINGERPRINT_SALT", "GOOGLE_MAPS_API_KEY")}
    env |= {"DATABASE_URL": os.environ["DATABASE_URL"], "TEAM_FINGERPRINTS": "",
            "ATOMICMEMORY_API_URL": "http://127.0.0.1:4831", "ATOMICMEMORY_API_KEY": API_KEY,
            "TRAVELER_COOKIE_SECRET": "local-demo-cookie-secret-not-for-production", "PUBLIC_ORIGIN": "http://localhost:4830"}
    settings = load_settings(env)
    pool = create_pool(settings.database_url)
    await pool.open()
    await bootstrap_schema(pool)
    memory_client = atomicmemory_client(env["ATOMICMEMORY_API_URL"], API_KEY, 3)
    app = create_app(settings, Path(__file__).resolve().parents[2] / "web/out")

    @asynccontextmanager
    async def lifespan(app):
        legs = LegRepository(pool)
        app.state.services = Services(FixturePlanner(legs), legs, UsageRepository(pool, frozenset()),
                                      RateLimiter(pool, per_minute=100), None,
                                      AtomicMemoryPreferenceStore(memory_client, 3))
        yield

    app.router.lifespan_context = lifespan
    servers = [uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=4830, access_log=False)),
               uvicorn.Server(uvicorn.Config(build_fake_app(FakeAtomicMemory()), host="127.0.0.1", port=4831, access_log=False))]
    try:
        await asyncio.gather(*(server.serve() for server in servers))
    finally:
        await memory_client.aclose()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
