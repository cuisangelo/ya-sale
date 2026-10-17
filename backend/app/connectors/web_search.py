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


class FallbackSearch:
    def __init__(self, primary: Connector, secondary: Connector) -> None:
        self._primary = primary
        self._secondary = secondary

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        # An empty or failed primary must still yield the secondary source.
        try:
            hits = await self._primary.search(query, max_results)
        except Exception as exc:
            logger.warning("primary search failed (%s); using secondary", type(exc).__name__)
            hits = []
        if not hits:
            hits = await self._secondary.search(query, max_results)
        return [_hit(hit.url, hit.title, hit.content) for hit in hits]
