import copy
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.connectors.cruzdelsur import API_URL, CruzDelSurSource, SearchUnfinished
from app.departures.domain import LIMA

FIXTURES = Path(__file__).parent / "fixtures" / "cruzdelsur"
DAY = date(2026, 10, 22)


def fixture(name: str) -> dict | list:
    return json.loads((FIXTURES / f"{name}.json").read_text())


class FakeCruzDelSur:
    """Answers like one-api.cruzdelsur.com.pe did for Lima -> Trujillo on 22 Oct 2026."""

    def __init__(self, results=None, status=200):
        self.requests: list[httpx.Request] = []
        self._results = list(results or [fixture("search_result")])
        self._status = status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._status != 200:
            return httpx.Response(self._status, text="Forbidden")
        path = request.url.path.removeprefix("/api/v2")
        if path == "/config":
            return httpx.Response(200, json=fixture("config"))
        if path == "/places":
            return httpx.Response(200, json=fixture("places"))
        if path == "/search" and request.method == "POST":
            return httpx.Response(200, json=fixture("search_post"))
        if path.startswith("/search/"):
            return httpx.Response(200, json=self._results.pop(0) if len(self._results) > 1 else self._results[0])
        return httpx.Response(404)

    def searches(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == "POST"]


def source(fake: FakeCruzDelSur) -> CruzDelSurSource:
    return CruzDelSurSource(httpx.AsyncClient(transport=httpx.MockTransport(fake)), poll_interval_s=0)


def pending_result() -> dict:
    result = copy.deepcopy(fixture("search_result"))
    result["state"] = "pending"
    result["trips"] = []
    return result


async def test_each_recorded_trip_becomes_a_departure_linked_to_its_seat_page():
    departures = await source(FakeCruzDelSur()).departures("Lima", "Trujillo", DAY)
    trip_id = fixture("search_result")["trips"][0]["id"]
    assert departures[0].operator == "Cruz del Sur · Evolution"
    assert departures[0].departs_at == datetime(2026, 10, 22, 9, 5, tzinfo=LIMA)
    assert departures[0].arrives_at == datetime(2026, 10, 22, 19, 50, tzinfo=LIMA)
    assert departures[0].price_pen == Decimal("85")
    assert departures[0].seats_available == 46
    assert departures[0].booking_url == f"https://viajes.cruzdelsur.com.pe/purchase/{trip_id}/new/A1"
    assert departures[0].seller == "cruzdelsur.com.pe"
    assert [(d.departs_at.hour, d.seats_available, d.price_pen) for d in departures] == [
        (9, 46, Decimal("85")),
        (21, 48, Decimal("100")),
        (22, 2, Decimal("140")),
    ]


async def test_the_search_uses_their_slugs_day_format_and_public_key():
    fake = FakeCruzDelSur()
    await source(fake).departures("LIMA", "Trujillo", DAY)
    [search] = fake.searches()
    assert json.loads(search.content) == {
        "origin": "lima",
        "destination": "trujillo",
        "date": "22-10-2026",
        "passengers": ["adult"],
        "way": "departure",
        "round": False,
    }
    assert search.headers["authorization"] == "Token token=fixture-desktop-key"
    assert search.headers["origin"] == "https://viajes.cruzdelsur.com.pe"
    assert str(search.url) == f"{API_URL}/search"


async def test_polls_until_the_search_is_finished():
    fake = FakeCruzDelSur(results=[pending_result(), fixture("search_result")])
    departures = await source(fake).departures("Lima", "Trujillo", DAY)
    assert len(departures) == 3
    assert sum(r.url.path.startswith("/api/v2/search/") for r in fake.requests) == 2


async def test_a_place_they_do_not_serve_finds_nothing_without_searching():
    fake = FakeCruzDelSur()
    assert await source(fake).departures("Lima", "Barranca", DAY) == []
    assert fake.searches() == []


async def test_trips_that_cannot_be_bought_or_leave_another_day_are_dropped():
    result = copy.deepcopy(fixture("search_result"))
    result["trips"][0]["is_buyable"] = False
    result["trips"][1]["departure"] = "2026-10-23T01:15:00"
    departures = await source(FakeCruzDelSur(results=[result])).departures("Lima", "Trujillo", DAY)
    assert [d.departs_at.hour for d in departures] == [22]


async def test_a_search_that_never_finishes_raises():
    with pytest.raises(SearchUnfinished):
        await source(FakeCruzDelSur(results=[pending_result()])).departures("Lima", "Trujillo", DAY)


async def test_a_blocked_request_raises_instead_of_finding_nothing():
    with pytest.raises(httpx.HTTPStatusError):
        await source(FakeCruzDelSur(status=403)).departures("Lima", "Trujillo", DAY)


async def test_config_and_places_are_fetched_once_per_instance():
    fake = FakeCruzDelSur()
    cds = source(fake)
    await cds.departures("Lima", "Trujillo", DAY)
    await cds.departures("Lima", "Trujillo", DAY)
    assert sum(r.url.path in ("/api/v2/config", "/api/v2/places") for r in fake.requests) == 2
