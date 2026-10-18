import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Literal

from app.departures.domain import Departure
from app.reader.discovery import Discoverer
from app.reader.domain import OperatorSite, Query, Recipe
from app.reader.extraction import DepartureExtractor
from app.reader.replay import replay
from app.reader.repository import RecipeRepository, ResultRepository
from app.reader.usage import Usage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Read:
    status: Literal["departures", "no_departures", "blocked", "unreadable"]
    departures: tuple[Departure, ...]
    discovered: bool
    usage: Usage


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ReaderService:
    """Reads one operator's departures: replay its recipe, and rediscover it once when the replay misses."""

    def __init__(
        self,
        recipes: RecipeRepository,
        results: ResultRepository,
        discoverer: Discoverer,
        extractor: DepartureExtractor,
        open_tab: Callable[[], AbstractAsyncContextManager],
        clock: Callable[[], datetime] = _now,
    ):
        self._recipes = recipes
        self._results = results
        self._discoverer = discoverer
        self._extractor = extractor
        self._open_tab = open_tab
        self._clock = clock

    async def read(self, site: OperatorSite, query: Query) -> Read:
        recipe = await self._recipes.find(site.domain, query)
        if recipe is not None and recipe.status == "blocked":
            return await self._finish(site, query, Read("blocked", (), False, Usage()))
        usage = Usage()
        if recipe is not None:
            found = await self._replay(site, recipe, query)
            if found.status != "unreadable":
                return await self._finish(site, query, found)
            logger.warning("reader: %s recipe for %s no longer reaches a results page; rediscovering", site.domain, recipe.route_key)
            await self._recipes.forget(recipe)
            usage = found.usage
        async with self._open_tab() as screen:
            discovery = await self._discoverer.discover(screen, site.domain, site.start_url, query)
        usage = usage + discovery.usage
        logger.info(
            "reader: discovery on %s %s: %s after %d actions, cost_usd=%s",
            site.domain, query.route_key, discovery.outcome, discovery.actions, discovery.usage.cost_usd,
        )
        if discovery.recipe is not None:
            await self._recipes.save(discovery.recipe, site.compliance_note)
        if discovery.outcome != "results" or discovery.recipe is None:
            status = "blocked" if discovery.outcome == "blocked" else "unreadable"
            return await self._finish(site, query, Read(status, (), True, usage))
        found = await self._replay(site, discovery.recipe, query)
        return await self._finish(site, query, Read(found.status, found.departures, True, usage + found.usage))

    async def _replay(self, site: OperatorSite, recipe: Recipe, query: Query) -> Read:
        found = await self._replay_once(site, recipe, query)
        if found.status != "unreadable" or recipe.url_template is None or not recipe.steps:
            return found
        # The results URL only worked inside the discovery's session: keep the clicks for this route instead.
        clicks = replace(recipe, route_key=query.route_key, url_template=None, submit_label=None)
        by_clicks = await self._replay_once(site, clicks, query)
        if by_clicks.status != "unreadable":
            await self._recipes.save(clicks, site.compliance_note)
        return replace(by_clicks, usage=found.usage + by_clicks.usage)

    async def _replay_once(self, site: OperatorSite, recipe: Recipe, query: Query) -> Read:
        async with self._open_tab() as screen:
            page = await replay(screen, recipe, query)
        # Each tab is a fresh visitor, so a URL-template page that rendered here opens the same for anyone.
        # A clicked-through page may live in the session, so its rows link to the search page instead.
        booking_url = page.url if recipe.url_template is not None else site.start_url
        extraction = await self._extractor.extract(
            page.text, page.url, site.name, site.domain, query.origin, query.destination, query.travel_date, booking_url
        )
        status = "unreadable" if extraction.page == "not_results" else extraction.page
        return Read(status, extraction.departures, False, extraction.usage)

    async def _finish(self, site: OperatorSite, query: Query, found: Read) -> Read:
        await self._results.store(site.domain, query, found.departures, self._clock())
        logger.info(
            "reader: %s %s %s: %s, %d departures, cost_usd=%s",
            site.domain, query.route_key, query.travel_date, found.status, len(found.departures), found.usage.cost_usd,
        )
        return found
