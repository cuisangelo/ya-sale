import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import anthropic
from fastapi import FastAPI

from app.api.guards import RateLimiter
from app.api.routes import router
from app.compare.service import CompareService
from app.config import Settings, load_settings
from app.connectors.extractor import LegExtractor
from app.connectors.web_search import ExaConnector, FallbackSearch, SearchBudget, TavilyConnector
from app.db import bootstrap_schema, create_pool
from app.legs.repository import LegRepository
from app.mcp_server import build_mcp
from app.trips.planner import MAX_SEARCHES_PER_TRIP, TripPlanner
from app.usage.repository import UsageRepository

TRIPS_PER_MINUTE_PER_FINGERPRINT = 6


@dataclass
class Services:
    planner: Any
    legs: LegRepository
    usage: UsageRepository
    limiter: RateLimiter
    compare: Any


def build_services(settings: Settings, pool) -> Services:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    legs = LegRepository(pool)
    search = FallbackSearch(TavilyConnector(settings.tavily_api_key), ExaConnector(settings.exa_api_key))
    planner = TripPlanner(legs, LegExtractor(client), search, lambda: SearchBudget(MAX_SEARCHES_PER_TRIP))
    return Services(
        planner=planner,
        legs=legs,
        usage=UsageRepository(pool, settings.team_fingerprints),
        limiter=RateLimiter(per_minute=TRIPS_PER_MINUTE_PER_FINGERPRINT),
        compare=CompareService(client, planner),
    )


def create_app(settings: Settings) -> FastAPI:
    mcp = build_mcp(lambda: app.state.services)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        pool = create_pool(settings.database_url)
        await pool.open()
        await bootstrap_schema(pool)
        app.state.services = build_services(settings, pool)
        async with mcp.session_manager.run():
            yield
        await pool.close()

    app = FastAPI(title="Ya Sale", lifespan=lifespan)
    app.state.settings = settings
    # Bound to 0.0.0.0 so the deployed hostname is accepted, not only localhost.
    app.mount("/mcp", mcp.streamable_http_app(streamable_http_path="/", stateless_http=True, host="0.0.0.0"))

    @app.get("/api/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(router)
    return app


def build_app() -> FastAPI:
    return create_app(load_settings(os.environ))
