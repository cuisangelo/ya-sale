import pytest

from app.connectors.base import SearchHit
from app.connectors.web_search import (
    AllSourcesFailed,
    BudgetExhausted,
    CombinedSearch,
    SearchBudget,
    TavilyConnector,
)

HIT = SearchHit(url="https://example.pe/a", title="Lima", content="bus every hour")


class _Raising:
    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        raise RuntimeError("primary down")


class _Fixed:
    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls = 0

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        self.calls += 1
        return self.hits


async def test_combined_search_merges_both_sources_without_duplicates():
    other = SearchHit(url="https://example.pe/b", title="Sauce", content="S/ 15")
    hits = await CombinedSearch(_Fixed([HIT]), _Fixed([HIT, other])).search("q", 5)
    assert [h.url for h in hits] == [HIT.url, other.url]


async def test_combined_search_survives_one_failing_source(caplog):
    hits = await CombinedSearch(_Raising(), _Fixed([HIT])).search("q", 5)
    assert hits == [HIT]
    assert "search source failed" in caplog.text


async def test_combined_search_fails_loud_when_both_fail():
    with pytest.raises(AllSourcesFailed):
        await CombinedSearch(_Raising(), _Raising()).search("q", 5)


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
