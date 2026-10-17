from datetime import UTC, datetime
from decimal import Decimal

import httpx

from app.legs.domain import LegData, LegKey
from app.main import create_app
from app.mcp_server import build_mcp
from app.trips.events import LegRefreshed, TripDone, TripStarted


class FakePlanner:
    def __init__(self, repo):
        self._repo = repo

    async def plan(self, origin, destination, date, trip_id):
        yield TripStarted(trip_id, origin, destination, 1)
        key = LegKey.of(origin, destination, "bus")
        data = LegData("Terminal", None, Decimal(80), Decimal(120), 1500, None, None)
        version = await self._repo.record_version(key, data, "https://a.pe", datetime.now(UTC))
        yield LegRefreshed(0, await self._repo.leg_id_of(key), "bus", origin, destination, "extracted", version)
        yield TripDone(1)


async def test_mcp_lists_three_tools():
    server = build_mcp(lambda: None)
    names = {tool.name for tool in await server.list_tools()}
    assert names == {"plan_trip", "get_leg", "confirm_leg"}


async def test_plan_trip_tool_returns_legs_with_sources(pool):
    from app.legs.repository import LegRepository

    legs = LegRepository(pool)
    services = type("S", (), {"planner": FakePlanner(legs), "legs": legs})()
    server = build_mcp(lambda: services)
    result = await server.call_tool("plan_trip", {"origin": "Lima", "destination": "Tarapoto", "date": "2026-10-25"})
    text = str(result)
    assert "https://a.pe" in text
    assert "extracted" in text


async def test_mcp_without_trailing_slash_works_next_to_the_web(settings, tmp_path):
    (tmp_path / "index.html").write_text("<h1>Ya Sale</h1>")
    app = create_app(settings, web_dir=tmp_path)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ya-sale.example") as client:
            response = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                headers={"Accept": "application/json, text/event-stream"},
            )
    assert response.status_code == 200
    assert "plan_trip" in response.text


async def test_mcp_endpoint_is_mounted(settings):
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ya-sale.example") as client:
            response = await client.post(
                "/mcp/",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                headers={"Accept": "application/json, text/event-stream"},
            )
    assert response.status_code == 200
    assert "plan_trip" in response.text
