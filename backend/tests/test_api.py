import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.api.guards import RateLimiter
from app.departures.domain import LIMA, Departure
from app.legs.domain import LegData, LegKey, LegOption
from app.legs.repository import LegRepository
from app.main import Services, create_app
from app.places.domain import MapPoint
from app.trips.domain import PlannedHop
from app.trips.events import LegDepartures, LegRefreshed, TripDone, TripMapped, TripStarted
from app.usage.repository import UsageRepository

BODY = {"origin": "Cusco", "destination": "Aguas Calientes", "date": "2026-10-25"}
KEY = LegKey.of("Cusco", "Ollantaytambo", "combi")


def leg_data(price=(10, 15)) -> LegData:
    return LegData("Paradero", None, Decimal(price[0]), Decimal(price[1]), 90, None, None)


FINAL_STOP = MapPoint("Ollantaytambo", -13.26, -72.26)


class FakePlanner:
    def __init__(self, repo, points=(MapPoint("Cusco", -13.53, -71.97), FINAL_STOP)):
        self._repo = repo
        self._points = points

    async def plan(self, origin, destination, date, trip_id):
        yield TripStarted(trip_id, origin, destination, 1, (PlannedHop("Cusco", "Ollantaytambo", ("combi",)),))
        version = await self._repo.record_version(KEY, leg_data(), "https://a.pe", datetime.now(UTC))
        leg_id = await self._repo.leg_id_of(KEY)
        option = LegOption(leg_data(price=(12, 12)), "https://b.pe", datetime.now(UTC))
        yield LegRefreshed(0, leg_id, "combi", "Cusco", "Ollantaytambo", "extracted", version, (option,))
        departure = Departure("Movil Bus", datetime(2026, 10, 25, 19, 30, tzinfo=LIMA), None, Decimal(35), 12, "https://movilbus.pe/x", "movilbus.pe")
        yield LegDepartures(0, "bus", (departure,))
        yield TripMapped(self._points)
        yield TripDone(1)


async def build_api(pool, settings, **planner_args):
    app = create_app(settings)
    legs = LegRepository(pool)
    app.state.services = Services(
        planner=FakePlanner(legs, **planner_args),
        legs=legs,
        usage=UsageRepository(pool, settings.team_fingerprints),
        limiter=RateLimiter(pool, per_minute=6),
        compare=None,
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def api(pool, settings):
    async with await build_api(pool, settings) as client:
        yield client


@pytest.fixture
async def api_without_final_point(pool, settings):
    async with await build_api(pool, settings, points=(MapPoint("Cusco", -13.53, -71.97),)) as client:
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
    assert [name for name, _ in events] == ["trip_started", "leg_refreshed", "leg_departures", "trip_mapped", "trip_done"]
    assert events[0][1]["hops"] == [{"origin": "Cusco", "destination": "Ollantaytambo", "modes": ["combi"]}]
    assert events[3][1] == {"points": [
        {"name": "Cusco", "lat": -13.53, "lng": -71.97},
        {"name": "Ollantaytambo", "lat": -13.26, "lng": -72.26},
    ]}
    leg = events[1][1]
    assert leg["options"] == [{
        "departure_point": "Paradero", "operator": None, "price_min_pen": "12", "price_max_pen": "12",
        "duration_min": 90, "schedule_note": None, "purchase_url": None,
        "source_url": "https://b.pe", "fetched_at": leg["options"][0]["fetched_at"],
    }]
    assert leg["version"]["source_url"] == "https://a.pe"
    assert leg["version"]["fetched_at"]
    assert leg["version"]["price_min_pen"] == "10"


async def test_leg_departures_event_carries_each_departure_in_lima_time(api):
    events = dict(sse_events((await api.post("/api/trips", json=BODY, headers=headers())).text))
    assert events["leg_departures"] == {
        "index": 0,
        "mode": "bus",
        "departures": [
            {
                "operator": "Movil Bus",
                "departs_at": "2026-10-25T19:30:00-05:00",
                "arrives_at": None,
                "price_pen": "35",
                "seats_available": 12,
                "booking_url": "https://movilbus.pe/x",
                "seller": "movilbus.pe",
            }
        ],
    }


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


async def test_compare_spends_the_same_budget_as_trips(api):
    for _ in range(6):
        await api.post("/api/trips", json=BODY, headers=headers())
    response = await api.post("/api/compare", json={"question": "Lima a Sauce sin tour"}, headers=headers())
    assert response.status_code == 429


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


async def stream_trip(api, request_headers):
    return await api.post("/api/trips", json=BODY, headers=request_headers)


async def insert_routed_trip(pool, origin, destination, created_at, fingerprint="visitor-fp"):
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO trips (origin, destination, fingerprint, created_at, resolved_destination, destination_lat, destination_lng)"
            " VALUES (%s, %s, %s, %s, %s, -13.26, -72.26)",
            (origin, destination, fingerprint, created_at, destination),
        )


async def test_recent_lists_routed_trips_with_their_resolved_place(api):
    await stream_trip(api, headers(ip="203.0.113.7"))
    body = (await api.get("/api/trips/recent")).json()
    assert body == [{"origin": "Cusco", "destination": "Aguas Calientes", "place": "Ollantaytambo",
                     "at": body[0]["at"], "lat": -13.26, "lng": -72.26}]
    assert "fingerprint" not in body[0]


async def test_recent_skips_trips_whose_last_stop_was_not_located(api_without_final_point):
    await stream_trip(api_without_final_point, headers())
    assert (await api_without_final_point.get("/api/trips/recent")).json() == []


async def test_recent_dedupes_case_insensitively_keeps_newest_and_caps_at_8(api, pool):
    for day in range(1, 11):
        await insert_routed_trip(pool, "Lima", f"Place {day}", datetime(2026, 10, day, tzinfo=UTC))
    await insert_routed_trip(pool, "lima", "PLACE 10", datetime(2026, 10, 11, tzinfo=UTC))
    body = (await api.get("/api/trips/recent")).json()
    assert [(t["origin"], t["destination"]) for t in body] == [
        ("lima", "PLACE 10"), ("Lima", "Place 9"), ("Lima", "Place 8"), ("Lima", "Place 7"),
        ("Lima", "Place 6"), ("Lima", "Place 5"), ("Lima", "Place 4"), ("Lima", "Place 3"),
    ]


async def test_recent_excludes_team_fingerprints(api, pool):
    await insert_routed_trip(pool, "Lima", "Cusco", datetime(2026, 10, 1, tzinfo=UTC), fingerprint="team-fp")
    assert (await api.get("/api/trips/recent")).json() == []


async def test_trip_stream_survives_a_failing_trip_resolution(api, monkeypatch, caplog):
    async def boom(*args):
        raise RuntimeError("pool timeout")

    monkeypatch.setattr(UsageRepository, "resolve_trip", boom)
    response = await api.post("/api/trips", json=BODY, headers=headers())
    assert [name for name, _ in sse_events(response.text)] == [
        "trip_started", "leg_refreshed", "leg_departures", "trip_mapped", "trip_done",
    ]
    assert "resolving trip" in caplog.text
