import asyncio
import logging

from exa_py import AsyncExa
from tavily import AsyncTavilyClient

from app.connectors.base import Connector, SearchHit

logger = logging.getLogger(__name__)

# Long pages blow the context window; keep the lead of each hit.
_MAX_CONTENT_CHARS = 12000


class BudgetExhausted(RuntimeError):
    pass


class SearchBudget:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._taken = 0

    def take(self) -> None:
        if self._taken >= self._limit:
            raise BudgetExhausted(f"search budget of {self._limit} is exhausted")
        self._taken += 1


def _clip(content: str) -> str:
    return content[:_MAX_CONTENT_CHARS]


def _hit(url: str, title: str, content: str) -> SearchHit:
    return SearchHit(url=url, title=title, content=_clip(content))


class TavilyConnector:
    def __init__(self, api_key: str) -> None:
        self.client = AsyncTavilyClient(api_key=api_key)

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        payload = await self.client.search(
            query,
            max_results=max_results,
            include_raw_content=True,
            country="peru",
        )
        hits: list[SearchHit] = []
        for item in payload["results"]:
            body = item.get("raw_content") or item.get("content") or ""
            hits.append(_hit(item["url"], item.get("title") or "", body))
        return hits


class ExaConnector:
    def __init__(self, api_key: str) -> None:
        self.client = AsyncExa(api_key=api_key)

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        response = await self.client.search_and_contents(
            query,
            num_results=max_results,
            text=True,
        )
        return [
            _hit(result.url or "", result.title or "", result.text or "")
            for result in response.results
        ]


class AllSourcesFailed(RuntimeError):
    pass


class CombinedSearch:
    """Queries every source concurrently and merges hits by URL, keeping source order."""

    def __init__(self, *sources: Connector) -> None:
        self._sources = sources

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        results = await asyncio.gather(*(s.search(query, max_results) for s in self._sources), return_exceptions=True)
        failures = [r for r in results if isinstance(r, BaseException)]
        for failure in failures:
            logger.warning("search source failed (%s)", type(failure).__name__)
        if len(failures) == len(results):
            raise AllSourcesFailed(query)
        merged: dict[str, SearchHit] = {}
        for hits in results:
            if not isinstance(hits, BaseException):
                for hit in hits:
                    merged.setdefault(hit.url, _hit(hit.url, hit.title, hit.content))
        return list(merged.values())
