import pytest

from app.connectors.base import SearchHit
from app.connectors.web_search import (
    BudgetExhausted,
    FallbackSearch,
    SearchBudget,
    TavilyConnector,
)

HIT = SearchHit(url="https://example.pe/a", title="Lima", content="bus every hour")


class _Raising:
    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        raise RuntimeError("primary down")


class _Empty:
    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        return []


class _Fixed:
    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls = 0

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        self.calls += 1
        return self.hits


async def test_fallback_used_when_primary_fails():
    secondary = _Fixed([HIT])
    hits = await FallbackSearch(_Raising(), secondary).search("lima cusco", 3)
    assert hits == [HIT]
    assert secondary.calls == 1


async def test_primary_failure_is_logged_not_swallowed(caplog):
    await FallbackSearch(_Raising(), _Fixed([HIT])).search("lima cusco", 3)
    assert "primary search failed" in caplog.text
    assert "RuntimeError" in caplog.text


async def test_fallback_used_when_primary_returns_nothing():
    secondary = _Fixed([HIT])
    hits = await FallbackSearch(_Empty(), secondary).search("lima cusco", 3)
    assert hits == [HIT]
    assert secondary.calls == 1


async def test_fallback_not_called_when_primary_has_results():
    secondary = _Fixed([SearchHit(url="https://other.pe", title="Other", content="no")])
    hits = await FallbackSearch(_Fixed([HIT]), secondary).search("lima cusco", 3)
    assert hits == [HIT]
    assert secondary.calls == 0


def test_budget_stops_at_limit():
    budget = SearchBudget(2)
    budget.take()
    budget.take()
    with pytest.raises(BudgetExhausted):
        budget.take()


class _FakeTavily:
    async def search(self, query, *, max_results, include_raw_content, country):
        return {
            "results": [
                {
                    "url": "https://example.pe/long",
                    "title": "Long page",
                    "content": "snippet",
                    "raw_content": "x" * 20000,
                }
            ]
        }


async def test_content_is_truncated():
    connector = TavilyConnector("test-key")
    connector.client = _FakeTavily()
    hits = await connector.search("lima", 1)
    assert len(hits) == 1
    assert hits[0].url == "https://example.pe/long"
    assert hits[0].title == "Long page"
    assert hits[0].content == "x" * 12000
