import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

from app.connectors.base import Connector
from app.connectors.extractor import ExtractedLeg, LegExtractor
from app.connectors.web_search import BudgetExhausted, SearchBudget
from app.legs.domain import LegKey, LegOption, Mode, completeness, display_version, distinct_options, has_price, leg_status
from app.legs.repository import LegRepository
from app.places.domain import GeocodingFailed, MapPoint, Point
from app.places.locator import PlaceLocator
from app.trips.domain import PlannedHop
from app.trips.events import LegError, LegRefreshed, LegStored, NoRoute, TripDone, TripEvent, TripMapped, TripStarted

logger = logging.getLogger(__name__)

MAX_SEARCHES_PER_TRIP = 12
RESULTS_PER_SEARCH = 5

NO_LIVE_DATA = "No encontramos datos en vivo para este tramo."
REFRESH_FAILED = "No pudimos actualizar este tramo ahora."


class TripPlanner:
    def __init__(
        self,
        repo: LegRepository,
        extractor: LegExtractor,
        search: Connector,
        budget_factory: Callable[[], SearchBudget],
        locator: PlaceLocator,
    ):
        self._repo = repo
        self._extractor = extractor
        self._search = search
        self._budget_factory = budget_factory
        self._locator = locator

    async def plan(self, origin: str, destination: str, date: str, trip_id: int) -> AsyncIterator[TripEvent]:
        budget = self._budget_factory()
        budget.take()
        pages = await self._search.search(f"cómo llegar de {origin} a {destination} transporte", RESULTS_PER_SEARCH)
        chain = await self._extractor.plan_chain(origin, destination, pages)
        if not chain:
            yield NoRoute(f"No encontramos cómo llegar de {origin} a {destination}. Revisa los nombres o prueba un lugar cercano.")
            return

        yield TripStarted(trip_id, origin, destination, len(chain), tuple(chain))
        for index, hop in enumerate(chain):
            for mode in hop.modes:
                key = LegKey.of(hop.origin, hop.destination, mode)
                versions = await self._repo.versions(key)
                if versions:
                    leg_id = await self._repo.leg_id_of(key)
                    options = await self._repo.options(key)
                    yield LegStored(index, leg_id, mode, hop.origin, hop.destination, leg_status(versions), display_version(versions), options)

        # Every leg's first search is funded before any refresh runs, main modes before alternatives,
        # so alternatives and price searches only spend what is left.
        legs = _by_priority(chain)
        funded = [_try_take(budget) for _ in legs]
        pending = [
            self._refresh(index, hop.origin, hop.destination, mode, ok, budget)
            for (index, hop, mode), ok in zip(legs, funded)
        ]
        pending.append(self._map(chain))
        for next_event in asyncio.as_completed(pending):
            yield await next_event
        yield TripDone(len(chain))

    async def _refresh(
        self, index: int, origin: str, destination: str, mode: Mode, funded: bool, budget: SearchBudget
    ) -> TripEvent:
        if not funded:
            return LegError(index, mode, NO_LIVE_DATA)
        try:
            pages = await self._search.search(f"{mode} {origin} a {destination} precio horario paradero", RESULTS_PER_SEARCH)
            extracted = await self._extractor.extract_legs(origin, destination, pages)
            if not any(has_price(leg.data) for leg in _matching(extracted, mode)):
                extracted += await self._price_candidates(origin, destination, mode, budget)
            matching = _matching(extracted, mode)
            if not matching:
                return LegError(index, mode, NO_LIVE_DATA)
            key = LegKey.of(origin, destination, mode)
            chosen = max(matching, key=lambda leg: completeness(leg.data))
            fetched_at = datetime.now(UTC)
            await self._repo.record_version(key, chosen.data, chosen.source_url, fetched_at)
            options = distinct_options([LegOption(leg.data, leg.source_url, fetched_at) for leg in matching])
            await self._repo.save_options(key, options)
            versions = await self._repo.versions(key)
            leg_id = await self._repo.leg_id_of(key)
            return LegRefreshed(index, leg_id, mode, origin, destination, leg_status(versions), display_version(versions), options)
        except Exception as exc:
            logger.warning("leg refresh failed (%s) for hop %d", type(exc).__name__, index)
            return LegError(index, mode, REFRESH_FAILED)

    async def _map(self, chain: list[PlannedHop]) -> TripMapped:
        names = list(dict.fromkeys(name for hop in chain for name in (hop.origin, hop.destination)))
        points = await asyncio.gather(*(self._locate(name) for name in names))
        return TripMapped(tuple(MapPoint(name, p.lat, p.lng) for name, p in zip(names, points) if p is not None))

    async def _locate(self, name: str) -> Point | None:
        # A place missing from the map never costs the trip its legs.
        try:
            return await self._locator.locate(name)
        except GeocodingFailed as exc:
            logger.warning("geocoding failed (%s)", exc)
            return None

    async def _price_candidates(self, origin: str, destination: str, mode: Mode, budget: SearchBudget) -> list[ExtractedLeg]:
        if not _try_take(budget):
            return []
        query = f"{mode} {origin} {destination} precio pasaje soles {datetime.now(UTC).year}"
        pages = await self._search.search(query, RESULTS_PER_SEARCH)
        return await self._extractor.extract_legs(origin, destination, pages)


def _by_priority(chain: list[PlannedHop]) -> list[tuple[int, PlannedHop, Mode]]:
    depth = max(len(hop.modes) for hop in chain)
    return [(index, hop, hop.modes[rank]) for rank in range(depth) for index, hop in enumerate(chain) if rank < len(hop.modes)]


def _try_take(budget: SearchBudget) -> bool:
    try:
        budget.take()
    except BudgetExhausted:
        return False
    return True


def _matching(legs: list[ExtractedLeg], mode: Mode) -> list[ExtractedLeg]:
    return [leg for leg in legs if leg.mode == mode] or legs
