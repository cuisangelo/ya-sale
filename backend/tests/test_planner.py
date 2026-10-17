from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.connectors.base import SearchHit
from app.connectors.extractor import ExtractedLeg
from app.connectors.web_search import SearchBudget
from app.legs.domain import LegData, LegKey
from app.legs.repository import LegRepository
from app.trips.events import LegError, LegRefreshed, LegStored, NoRoute, TripDone, TripStarted
from app.trips.planner import TripPlanner

DATE = "2026-10-25"
TWO_HOPS = [("Cusco", "Ollantaytambo", "combi"), ("Ollantaytambo", "Aguas Calientes", "tren")]
MANY_HOPS = [(f"P{i}", f"P{i + 1}", "bus") for i in range(10)]


def leg_data(price=(10, 15)) -> LegData:
    return LegData("Paradero", None, Decimal(price[0]), Decimal(price[1]), 90, None, None)


class FakeSearch:
    def __init__(self, failing_query_part: str | None = None):
        self.calls = 0
        self._failing = failing_query_part

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        self.calls += 1
        if self._failing and self._failing in query:
            raise RuntimeError("provider down")
        return [SearchHit(url=f"https://ejemplo.pe/{self.calls}", title="t", content="S/ 12")]


class FakeExtractor:
    def __init__(self, chain):
        self._chain = chain

    async def plan_chain(self, origin, destination, pages):
        return list(self._chain)

    async def extract_legs(self, origin, destination, pages):
        mode = next(m for a, b, m in self._chain if a == origin and b == destination)
        return [ExtractedLeg(origin, destination, mode, leg_data(), pages[0].url)]


@pytest.fixture
def repo(pool):
    return LegRepository(pool)


def planner(repo, chain, search=None):
    return TripPlanner(repo, FakeExtractor(chain), search or FakeSearch(), lambda: SearchBudget(8))


async def collect(p, origin, destination):
    return [e async for e in p.plan(origin, destination, DATE, trip_id=1)]


async def test_stored_leg_is_emitted_before_refresh(repo):
    await repo.record_version(LegKey.of("Cusco", "Ollantaytambo", "combi"), leg_data(), "https://a.pe", datetime.now(UTC))
    events = await collect(planner(repo, TWO_HOPS), "Cusco", "Aguas Calientes")
    kinds = [type(e).__name__ for e in events]
    assert kinds[0] == "TripStarted"
    assert kinds.index("LegStored") < kinds.index("LegRefreshed")
    assert kinds[-1] == "TripDone"


async def test_every_emitted_version_has_source_and_fetched_at(repo):
    events = await collect(planner(repo, TWO_HOPS), "Cusco", "Aguas Calientes")
    legs = [e for e in events if isinstance(e, (LegStored, LegRefreshed))]
    assert len(legs) == 2
    for event in legs:
        assert event.version.source_url and event.version.fetched_at


async def test_unknown_place_yields_no_route_not_invented_legs(repo):
    events = await collect(planner(repo, []), "Xyzabc", "San Juan")
    assert [type(e).__name__ for e in events] == ["NoRoute"]
    assert "no encontramos" in events[0].message.lower()


async def test_provider_failure_on_one_leg_keeps_others(repo):
    await repo.record_version(LegKey.of("Cusco", "Ollantaytambo", "combi"), leg_data(), "https://a.pe", datetime.now(UTC))
    search = FakeSearch(failing_query_part="Cusco a Ollantaytambo")
    events = await collect(planner(repo, TWO_HOPS, search), "Cusco", "Aguas Calientes")
    assert any(isinstance(e, LegError) and e.index == 0 for e in events)
    assert any(isinstance(e, LegStored) and e.index == 0 for e in events)
    assert any(isinstance(e, LegRefreshed) and e.index == 1 for e in events)
    assert isinstance(events[-1], TripDone)


async def test_search_budget_is_respected(repo):
    search = FakeSearch()
    events = await collect(planner(repo, MANY_HOPS, search), "P0", "P10")
    assert search.calls <= 8
    assert isinstance(events[0], TripStarted) and events[0].legs_planned == 10
    assert sum(isinstance(e, LegError) for e in events) >= 3
