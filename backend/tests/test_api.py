import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.api.guards import RateLimiter
from app.legs.domain import LegData, LegKey
from app.legs.repository import LegRepository
from app.main import Services, create_app
from app.trips.events import LegRefreshed, TripDone, TripStarted
from app.usage.repository import UsageRepository

BODY = {"origin": "Cusco", "destination": "Aguas Calientes", "date": "2026-10-25"}
KEY = LegKey.of("Cusco", "Ollantaytambo", "combi")


def leg_data(price=(10, 15)) -> LegData:
    return LegData("Paradero", None, Decimal(price[0]), Decimal(price[1]), 90, None, None)


class FakePlanner:
    def __init__(self, repo):
        self._repo = repo

    async def plan(self, origin, destination, date, trip_id):
        yield TripStarted(trip_id, origin, destination, 1)
        version = await self._repo.record_version(KEY, leg_data(), "https://a.pe", datetime.now(UTC))
        leg_id = await self._repo.leg_id_of(KEY)
        yield LegRefreshed(0, leg_id, "combi", "Cusco", "Ollantaytambo", "extracted", version)
        yield TripDone(1)


@pytest.fixture
async def api(pool, settings):
    app = create_app(settings)
    legs = LegRepository(pool)
    app.state.services = Services(
        planner=FakePlanner(legs),
        legs=legs,
        usage=UsageRepository(pool, settings.team_fingerprints),
        limiter=RateLimiter(per_minute=6),
        compare=None,
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


def headers(ip="198.51.100.1", agent="test-agent"):
    return {"X-Forwarded-For": ip, "User-Agent": agent}


def sse_events(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def test_trip_stream_events(api):
    response = await api.post("/api/trips", json=BODY, headers=headers())
    assert response.headers["content-type"].startswith("text/event-stream")
    events = sse_events(response.text)
    assert [name for name, _ in events] == ["trip_started", "leg_refreshed", "trip_done"]
    leg = events[1][1]
    assert leg["version"]["source_url"] == "https://a.pe"
    assert leg["version"]["fetched_at"]
    assert leg["version"]["price_min_pen"] == "10"


async def test_confirmation_returns_confirmed_leg(api):
    events = sse_events((await api.post("/api/trips", json=BODY, headers=headers())).text)
    leg = events[1][1]
    response = await api.post(f"/api/legs/{leg['leg_id']}/confirmations", json={"version_id": leg["version"]["id"], "display_name": "Ana"}, headers=headers())
    assert response.status_code == 201
    assert response.json()["status"] == "confirmed"


async def test_repeat_confirmation_is_409(api):
    leg = sse_events((await api.post("/api/trips", json=BODY, headers=headers())).text)[1][1]
    body = {"version_id": leg["version"]["id"]}
    await api.post(f"/api/legs/{leg['leg_id']}/confirmations", json=body, headers=headers())
    again = await api.post(f"/api/legs/{leg['leg_id']}/confirmations", json=body, headers=headers())
    assert again.status_code == 409
    assert again.json()["detail"] == "Ya confirmaste este tramo."


async def test_correction_creates_confirmed_version(api):
    leg = sse_events((await api.post("/api/trips", json=BODY, headers=headers())).text)[1][1]
    response = await api.post(f"/api/legs/{leg['leg_id']}/corrections", json={"price_min_pen": "30", "price_max_pen": "35"}, headers=headers())
    assert response.status_code == 201
    assert response.json()["version"]["source_url"] == "ya-sale:confirmation"


async def test_unknown_leg_is_404(api):
    assert (await api.get("/api/legs/999")).status_code == 404


async def test_usage_counts_come_from_db(api):
    await api.post("/api/trips", json=BODY, headers=headers(ip="198.51.100.1"))
    await api.post("/api/trips", json=BODY | {"destination": "Ollantaytambo"}, headers=headers(ip="198.51.100.2"))
    usage = (await api.get("/api/usage")).json()
    assert usage["trips"] == 2
    assert usage["people"] == 2
    assert usage["destinations"] == 2


async def test_usage_excludes_team_fingerprints(api, settings, monkeypatch):
    from app.api import guards

    monkeypatch.setattr(guards, "fingerprint", lambda request, salt: "team-fp")
    await api.post("/api/trips", json=BODY, headers=headers())
    usage = (await api.get("/api/usage")).json()
    assert usage["trips"] == 0 and usage["people"] == 0


async def test_rate_limit_returns_429_after_6_trips_per_minute(api):
    statuses = [(await api.post("/api/trips", json=BODY, headers=headers())).status_code for _ in range(7)]
    assert statuses[:6] == [200] * 6
    assert statuses[6] == 429


async def test_raw_ip_never_logged(api, caplog):
    caplog.set_level(logging.DEBUG)
    await api.post("/api/trips", json=BODY, headers=headers(ip="203.0.113.9"))
    assert "203.0.113.9" not in caplog.text


def test_fingerprint_is_stable_and_salted():
    from starlette.requests import Request

    from app.api.guards import fingerprint

    scope = {"type": "http", "headers": [(b"x-forwarded-for", b"203.0.113.9, 10.0.0.1"), (b"user-agent", b"ua")], "client": ("10.0.0.1", 1)}
    first = fingerprint(Request(scope), "salt-a")
    assert first == fingerprint(Request(scope), "salt-a")
    assert first != fingerprint(Request(scope), "salt-b")
    assert "203.0.113.9" not in first and len(first) == 16
