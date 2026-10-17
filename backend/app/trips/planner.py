import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

from app.connectors.base import Connector
from app.connectors.extractor import LegExtractor
from app.connectors.web_search import BudgetExhausted, SearchBudget
from app.legs.domain import LegKey, Mode, display_version, leg_status
from app.legs.repository import LegRepository
from app.trips.events import LegError, LegRefreshed, LegStored, NoRoute, TripDone, TripEvent, TripStarted

logger = logging.getLogger(__name__)

MAX_SEARCHES_PER_TRIP = 8
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
    ):
        self._repo = repo
        self._extractor = extractor
        self._search = search
        self._budget_factory = budget_factory

    async def plan(self, origin: str, destination: str, date: str, trip_id: int) -> AsyncIterator[TripEvent]:
        budget = self._budget_factory()
        budget.take()
        pages = await self._search.search(f"cómo llegar de {origin} a {destination} transporte", RESULTS_PER_SEARCH)
        chain = await self._extractor.plan_chain(origin, destination, pages)
        if not chain:
            yield NoRoute(f"No encontramos cómo llegar de {origin} a {destination}. Revisa los nombres o prueba un lugar cercano.")
            return

        yield TripStarted(trip_id, origin, destination, len(chain))
        for index, (hop_origin, hop_destination, mode) in enumerate(chain):
            key = LegKey.of(hop_origin, hop_destination, mode)
            versions = await self._repo.versions(key)
            if versions:
                leg_id = await self._repo.leg_id_of(key)
                yield LegStored(index, leg_id, mode, hop_origin, hop_destination, leg_status(versions), display_version(versions))

        refreshes = [self._refresh(index, *hop, budget) for index, hop in enumerate(chain)]
        for next_event in asyncio.as_completed(refreshes):
            yield await next_event
        yield TripDone(len(chain))

    async def _refresh(self, index: int, origin: str, destination: str, mode: Mode, budget: SearchBudget) -> TripEvent:
        try:
            budget.take()
            pages = await self._search.search(f"{mode} {origin} a {destination} precio horario paradero", RESULTS_PER_SEARCH)
            extracted = await self._extractor.extract_legs(origin, destination, pages)
            matching = [leg for leg in extracted if leg.mode == mode] or extracted
            if not matching:
                return LegError(index, NO_LIVE_DATA)
            key = LegKey.of(origin, destination, mode)
            chosen = matching[0]
            await self._repo.record_version(key, chosen.data, chosen.source_url, datetime.now(UTC))
            versions = await self._repo.versions(key)
            leg_id = await self._repo.leg_id_of(key)
            return LegRefreshed(index, leg_id, mode, origin, destination, leg_status(versions), display_version(versions))
        except BudgetExhausted:
            return LegError(index, NO_LIVE_DATA)
        except Exception as exc:
            logger.warning("leg refresh failed (%s) for hop %d", type(exc).__name__, index)
            return LegError(index, REFRESH_FAILED)
