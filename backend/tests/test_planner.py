import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.connectors.base import SearchHit
from app.connectors.extractor import ExtractedLeg
from app.connectors.web_search import SearchBudget
from app.departures.domain import LIMA, Departure
from app.legs.domain import LegData, LegKey, Mode
from app.places.domain import GeocodingFailed, Point
from app.legs.repository import LegRepository
from app.trips.domain import PlannedHop
from app.trips.events import LegDepartures, LegError, LegRefreshed, LegStored, NoRoute, TripDone, TripMapped, TripStarted
from app.trips import planner as planner_module
from app.trips.planner import TripPlanner

DATE = "2026-10-25"
TWO_HOPS = [PlannedHop("Cusco", "Ollantaytambo", ("combi",)), PlannedHop("Ollantaytambo", "Aguas Calientes", ("tren",))]
MANY_HOPS = [PlannedHop(f"P{i}", f"P{i + 1}", ("bus",)) for i in range(10)]
BUS_OR_PLANE = [PlannedHop("Lima", "Tarapoto", ("bus", "avion")), PlannedHop("Tarapoto", "Sauce", ("colectivo",))]
PLACES = {"Cusco": Point(-13.53, -71.97), "Ollantaytambo": Point(-13.26, -72.26)}


def leg_data(price=(10, 15)) -> LegData:
    return LegData("Paradero", None, Decimal(price[0]), Decimal(price[1]), 90, None, None)


class FakeSearch:
    def __init__(self, failing_query_part: str | None = None):
        self.calls = 0
        self.queries: list[str] = []
        self._failing = failing_query_part

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        self.calls += 1
        self.queries.append(query)
        if self._failing and self._failing in query:
            raise RuntimeError("provider down")
        # The title carries the query so fake extractors can answer per query.
        return [SearchHit(url=f"https://ejemplo.pe/{self.calls}", title=query, content="S/ 12")]


class FakeExtractor:
    def __init__(self, chain):
        self._chain = chain
        self.chain_calls = 0

    async def plan_chain(self, origin, destination, pages):
        self.chain_calls += 1
        return list(self._chain)

    def modes(self, origin, destination):
        return next(hop.modes for hop in self._chain if (hop.origin, hop.destination) == (origin, destination))

    async def extract_legs(self, origin, destination, pages):
        return [ExtractedLeg(origin, destination, mode, leg_data(), pages[0].url) for mode in self.modes(origin, destination)]


class PerQueryExtractor(FakeExtractor):
    """Answers each hop with the candidates scripted for the query that found the pages."""

    def __init__(self, chain, candidates):
        super().__init__(chain)
        self._candidates = candidates

    async def extract_legs(self, origin, destination, pages):
        return [
            ExtractedLeg(origin, destination, mode, data, pages[0].url)
            for mode in self.modes(origin, destination)
            for data in self._candidates(pages[0].title)
        ]


class FakeLocator:
    def __init__(self, places=None, failing=()):
        self._places = PLACES if places is None else places
        self._failing = failing

    async def locate(self, name):
        if name in self._failing:
            raise GeocodingFailed("OVER_QUERY_LIMIT")
        return self._places.get(name)


def departure(hour: int, seller: str) -> Departure:
    return Departure("Movil Bus", datetime(2026, 10, 25, hour, 0, tzinfo=LIMA), None, Decimal(35), 12, f"https://{seller}/{hour}", seller)


class FakeDepartureSource:
    def __init__(self, seller: str, hours=(), error: Exception | None = None, delay: float = 0, mode: Mode = "bus"):
        self.seller = seller
        self.mode = mode
        self.calls: list[tuple[str, str, date]] = []
        self._hours = hours
        self._error = error
        self._delay = delay

    async def departures(self, origin, destination, travel_date):
        self.calls.append((origin, destination, travel_date))
        await asyncio.sleep(self._delay)
        if self._error:
            raise self._error
        return [departure(hour, self.seller) for hour in self._hours]


class FakeRoutes:
    def __init__(self):
        self.saved: dict[str, tuple[list[PlannedHop], datetime]] = {}

    async def cached(self, key, planned_after):
        found = self.saved.get(key)
        return found[0] if found and found[1] > planned_after else None

    async def store(self, key, chain, planned_at):
        self.saved[key] = (list(chain), planned_at)


def unpriced() -> LegData:
    return LegData("Terminal", None, None, None, 120, None, None)


def is_price_query(query: str) -> bool:
    return "pasaje soles" in query


@pytest.fixture
def repo(pool):
    return LegRepository(pool)


def planner(repo, chain, search=None, extractor=None, budget=8, locator=None, sources=(), routes=None):
    return TripPlanner(
        repo,
        extractor or FakeExtractor(chain),
        search or FakeSearch(),
        lambda: SearchBudget(budget),
        locator or FakeLocator(),
        sources,
        routes or FakeRoutes(),
    )


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


def refreshed(events) -> list[LegRefreshed]:
    return sorted((e for e in events if isinstance(e, LegRefreshed)), key=lambda e: e.index)


async def test_prefers_a_priced_candidate_over_an_earlier_unpriced_one(repo):
    extractor = PerQueryExtractor(TWO_HOPS, lambda query: [unpriced(), leg_data()])
    events = await collect(planner(repo, TWO_HOPS, extractor=extractor), "Cusco", "Aguas Calientes")
    assert [e.version.data.price_min_pen for e in refreshed(events)] == [Decimal(10), Decimal(10)]


async def test_searches_prices_when_no_candidate_has_one(repo):
    search = FakeSearch()
    extractor = PerQueryExtractor(TWO_HOPS, lambda query: [leg_data()] if is_price_query(query) else [unpriced()])
    events = await collect(planner(repo, TWO_HOPS, search, extractor), "Cusco", "Aguas Calientes")
    assert sum(is_price_query(q) for q in search.queries) == 2
    for event in refreshed(events):
        assert event.version.data.price_min_pen == Decimal(10)
        assert event.version.source_url in {f"https://ejemplo.pe/{i}" for i in range(1, search.calls + 1)}


async def test_skips_the_price_search_when_a_price_is_already_found(repo):
    search = FakeSearch()
    await collect(planner(repo, TWO_HOPS, search), "Cusco", "Aguas Calientes")
    assert not any(is_price_query(q) for q in search.queries)


async def test_keeps_the_unpriced_leg_when_the_price_search_finds_none(repo):
    extractor = PerQueryExtractor(TWO_HOPS, lambda query: [] if is_price_query(query) else [unpriced()])
    events = await collect(planner(repo, TWO_HOPS, extractor=extractor), "Cusco", "Aguas Calientes")
    assert [e.version.data.price_min_pen for e in refreshed(events)] == [None, None]


async def test_price_search_found_after_an_empty_first_search(repo):
    extractor = PerQueryExtractor(TWO_HOPS, lambda query: [leg_data()] if is_price_query(query) else [])
    events = await collect(planner(repo, TWO_HOPS, extractor=extractor), "Cusco", "Aguas Calientes")
    assert len(refreshed(events)) == 2


async def test_exhausted_budget_keeps_the_unpriced_leg_instead_of_failing(repo):
    search = FakeSearch()
    extractor = PerQueryExtractor(TWO_HOPS, lambda query: [unpriced()])
    events = await collect(planner(repo, TWO_HOPS, search, extractor, budget=3), "Cusco", "Aguas Calientes")
    assert search.calls == 3
    assert len(refreshed(events)) == 2


async def test_every_mode_of_a_hop_is_refreshed_as_its_own_leg(repo):
    events = await collect(planner(repo, BUS_OR_PLANE), "Lima", "Sauce")
    assert events[0].hops == tuple(BUS_OR_PLANE)
    assert sorted((e.index, e.mode) for e in refreshed(events)) == [(0, "avion"), (0, "bus"), (1, "colectivo")]


async def test_alternatives_never_take_the_search_of_a_main_mode(repo):
    search = FakeSearch()
    events = await collect(planner(repo, BUS_OR_PLANE, search, budget=3), "Lima", "Sauce")
    assert sorted((e.index, e.mode) for e in refreshed(events)) == [(0, "bus"), (1, "colectivo")]
    assert [(e.index, e.mode) for e in events if isinstance(e, LegError)] == [(0, "avion")]


async def test_refreshed_leg_carries_every_distinct_option_with_its_source(repo):
    extractor = PerQueryExtractor(TWO_HOPS, lambda query: [unpriced(), leg_data(), leg_data(price=(20, 25))])
    events = await collect(planner(repo, TWO_HOPS, extractor=extractor), "Cusco", "Aguas Calientes")
    options = refreshed(events)[0].options
    assert [o.data.price_min_pen for o in options] == [Decimal(10), Decimal(20), None]
    assert all(o.source_url.startswith("https://ejemplo.pe/") and o.fetched_at for o in options)


async def test_stored_leg_comes_back_with_its_stored_options(repo):
    await collect(planner(repo, TWO_HOPS), "Cusco", "Aguas Calientes")
    events = await collect(planner(repo, TWO_HOPS, search=FakeSearch(failing_query_part="precio horario")), "Cusco", "Aguas Calientes")
    stored = [e for e in events if isinstance(e, LegStored)]
    assert len(stored) == 2 and all(len(e.options) == 1 for e in stored)


async def test_map_has_only_the_places_that_were_located(repo):
    events = await collect(planner(repo, TWO_HOPS), "Cusco", "Aguas Calientes")
    mapped = next(e for e in events if isinstance(e, TripMapped))
    assert [(p.name, p.lat, p.lng) for p in mapped.points] == [("Cusco", -13.53, -71.97), ("Ollantaytambo", -13.26, -72.26)]


async def test_a_geocoding_failure_drops_that_place_and_keeps_the_trip(repo):
    events = await collect(planner(repo, TWO_HOPS, locator=FakeLocator(failing={"Cusco"})), "Cusco", "Aguas Calientes")
    mapped = next(e for e in events if isinstance(e, TripMapped))
    assert [p.name for p in mapped.points] == ["Ollantaytambo"]
    assert len(refreshed(events)) == 2


def departures_events(events) -> list[LegDepartures]:
    return [e for e in events if isinstance(e, LegDepartures)]


async def test_bus_hop_gets_the_departures_of_every_source_earliest_first(repo):
    sources = (FakeDepartureSource("a.pe", hours=(19, 7)), FakeDepartureSource("b.pe", hours=(13,)))
    events = await collect(planner(repo, BUS_OR_PLANE, sources=sources), "Lima", "Sauce")
    [found] = departures_events(events)
    assert (found.index, found.mode) == (0, "bus")
    assert [(d.departs_at.hour, d.seller) for d in found.departures] == [(7, "a.pe"), (13, "b.pe"), (19, "a.pe")]
    assert sources[0].calls == [("Lima", "Tarapoto", date(2026, 10, 25))]
    assert isinstance(events[-1], TripDone)


async def test_hops_without_a_bus_never_query_the_sources(repo):
    source = FakeDepartureSource("a.pe", hours=(7,))
    events = await collect(planner(repo, TWO_HOPS, sources=(source,)), "Cusco", "Aguas Calientes")
    assert source.calls == []
    assert departures_events(events) == []


async def test_each_mode_of_a_hop_gets_the_departures_of_its_own_sources(repo):
    bus, plane = FakeDepartureSource("bus.pe", hours=(7,)), FakeDepartureSource("sky.pe", hours=(9, 6), mode="avion")
    events = await collect(planner(repo, BUS_OR_PLANE, sources=(bus, plane)), "Lima", "Sauce")
    found = {(e.index, e.mode): [(d.departs_at.hour, d.seller) for d in e.departures] for e in departures_events(events)}
    assert found == {(0, "bus"): [(7, "bus.pe")], (0, "avion"): [(6, "sky.pe"), (9, "sky.pe")]}
    assert bus.calls == plane.calls == [("Lima", "Tarapoto", date(2026, 10, 25))]


async def test_a_source_is_never_asked_for_a_mode_it_does_not_serve(repo):
    plane = FakeDepartureSource("sky.pe", hours=(9,), mode="avion")
    chain = [PlannedHop("Lima", "Trujillo", ("bus",)), PlannedHop("Trujillo", "Huanchaco", ("combi",))]
    events = await collect(planner(repo, chain, sources=(plane,)), "Lima", "Huanchaco")
    assert plane.calls == []
    assert departures_events(events) == []


async def test_a_failing_source_is_logged_and_leaves_the_trip_and_other_sources_intact(repo, caplog):
    caplog.set_level(logging.WARNING)
    sources = (FakeDepartureSource("roto.pe", error=RuntimeError("403 Forbidden")), FakeDepartureSource("b.pe", hours=(13,)))
    events = await collect(planner(repo, BUS_OR_PLANE, sources=sources), "Lima", "Sauce")
    [found] = departures_events(events)
    assert [d.seller for d in found.departures] == ["b.pe"]
    assert sorted((e.index, e.mode) for e in refreshed(events)) == [(0, "avion"), (0, "bus"), (1, "colectivo")]
    assert "roto.pe" in caplog.text and "403 Forbidden" in caplog.text


async def test_no_departures_emits_nothing(repo):
    events = await collect(planner(repo, BUS_OR_PLANE, sources=(FakeDepartureSource("a.pe"),)), "Lima", "Sauce")
    assert departures_events(events) == []
    assert isinstance(events[-1], TripDone)


async def test_a_slow_source_is_dropped_without_holding_the_trip(repo, monkeypatch, caplog):
    monkeypatch.setattr(planner_module, "DEPARTURES_TIMEOUT_S", 0.01)
    caplog.set_level(logging.WARNING)
    source = FakeDepartureSource("lento.pe", hours=(7,), delay=1)
    events = await collect(planner(repo, BUS_OR_PLANE, sources=(source,)), "Lima", "Sauce")
    assert departures_events(events) == []
    assert "lento.pe" in caplog.text


async def test_a_date_that_is_not_a_day_skips_departures_but_keeps_the_trip(repo):
    source = FakeDepartureSource("a.pe", hours=(7,))
    events = [e async for e in planner(repo, BUS_OR_PLANE, sources=(source,)).plan("Lima", "Sauce", "el sábado", trip_id=1)]
    assert source.calls == []
    assert isinstance(events[-1], TripDone) and len(refreshed(events)) == 3


async def test_a_planned_route_is_reused_without_searching_or_asking_the_model_again(repo):
    search, extractor = FakeSearch(), FakeExtractor(TWO_HOPS)
    p = planner(repo, TWO_HOPS, search=search, extractor=extractor)
    first = await collect(p, "Cusco", "Aguas Calientes")
    queries_before = len(search.queries)
    second = await collect(p, "cusco ", "AGUAS CALIENTES")
    assert extractor.chain_calls == 1
    assert not any("cómo llegar" in q for q in search.queries[queries_before:])
    assert first[0].hops == second[0].hops


async def test_no_route_is_never_remembered(repo):
    routes = FakeRoutes()
    await collect(planner(repo, [], routes=routes), "Xyzabc", "San Juan")
    assert routes.saved == {}


async def test_a_route_older_than_a_week_is_planned_again(repo):
    routes, extractor = FakeRoutes(), FakeExtractor(TWO_HOPS)
    p = planner(repo, TWO_HOPS, extractor=extractor, routes=routes)
    await collect(p, "Cusco", "Aguas Calientes")
    key = next(iter(routes.saved))
    routes.saved[key] = (routes.saved[key][0], datetime.now(UTC) - timedelta(days=8))
    await collect(p, "Cusco", "Aguas Calientes")
    assert extractor.chain_calls == 2
