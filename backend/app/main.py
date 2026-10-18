import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anthropic
import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.guards import RateLimiter
from app.api.routes import router
from app.compare.service import CompareService
from app.config import Settings, load_settings
from app.connectors.cruzdelsur import CruzDelSurSource
from app.connectors.extractor import LegExtractor
from app.connectors.geocoding import GoogleGeocoder
from app.connectors.linea import LineaSource
from app.connectors.oltursa import OltursaSource
from app.connectors.web_search import CombinedSearch, ExaConnector, SearchBudget, TavilyConnector
from app.db import bootstrap_schema, create_pool
from app.legs.repository import LegRepository
from app.mcp_server import build_mcp
from app.places.locator import PlaceLocator
from app.places.repository import PlaceRepository
from app.trips.planner import MAX_SEARCHES_PER_TRIP, TripPlanner
from app.trips.repository import RouteRepository
from app.usage.repository import UsageRepository

TRIPS_PER_MINUTE_PER_FINGERPRINT = 6
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


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
    search = CombinedSearch(TavilyConnector(settings.tavily_api_key), ExaConnector(settings.exa_api_key))
    locator = PlaceLocator(PlaceRepository(pool), GoogleGeocoder(settings.google_maps_api_key, httpx.AsyncClient(timeout=10)))
    departure_sources = (
        CruzDelSurSource(httpx.AsyncClient(timeout=10), poll_interval_s=1),
        OltursaSource(httpx.AsyncClient(timeout=10)),
        LineaSource(lambda: httpx.AsyncClient(timeout=10)),
    )
    planner = TripPlanner(
        legs, LegExtractor(client), search, lambda: SearchBudget(MAX_SEARCHES_PER_TRIP), locator, departure_sources, RouteRepository(pool)
    )
    return Services(
        planner=planner,
        legs=legs,
        usage=UsageRepository(pool, settings.team_fingerprints),
        limiter=RateLimiter(pool, per_minute=TRIPS_PER_MINUTE_PER_FINGERPRINT),
        compare=CompareService(client, planner),
    )


class McpWithoutTrailingSlash:
    """Routes POST /mcp to the MCP app; otherwise the static web mount answers it with 405."""

    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/mcp":
            scope = {**scope, "path": "/mcp/", "raw_path": b"/mcp/"}
        await self._app(scope, receive, send)


def create_app(settings: Settings, web_dir: Path | None = None) -> FastAPI:
    # httpx logs every request URL at INFO, and the geocoding key can only travel in the URL.
    logging.getLogger("httpx").setLevel(logging.WARNING)
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
    app.add_middleware(McpWithoutTrailingSlash)
    app.state.settings = settings
    # Bound to 0.0.0.0 so the deployed hostname is accepted, not only localhost.
    app.mount("/mcp", mcp.streamable_http_app(streamable_http_path="/", stateless_http=True, host="0.0.0.0"))

    @app.get("/api/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(router)
    # Mounted last so /api and /mcp keep priority over the static export.
    if web_dir is not None:
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app


def build_app() -> FastAPI:
    # The container image ships the web export here; local dev runs the API alone.
    web_dir = WEB_DIR if WEB_DIR.is_dir() else None
    return create_app(load_settings(os.environ), web_dir=web_dir)
