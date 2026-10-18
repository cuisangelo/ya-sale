from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.departures.domain import LIMA, Departure
from app.reader.domain import ANY_ROUTE, OperatorSite, Query, Recipe, Step
from app.reader.repository import RecipeRepository, RequestQueue, ResultRepository
from app.reader.source import BrowserOperatorSource

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
DAY = date(2026, 10, 20)
SITE = OperatorSite("bus.example", "Bus Example", "https://bus.example/", frozenset({"lima", "cajamarca"}), "robots allows /")
DEPARTURE = Departure(
    "Bus Example · Ejecutivo", datetime(2026, 10, 20, 16, 0, tzinfo=LIMA), None, Decimal("70"), 12,
    "https://bus.example/pasajes/lima/cajamarca?fecha=20-10-2026", "bus.example",
)


def _source(pool, now=NOW):
    return BrowserOperatorSource(SITE, ResultRepository(pool), RequestQueue(pool), clock=lambda: now)


async def test_a_miss_queues_the_search_once_and_answers_without_waiting(pool):
    source = _source(pool)

    assert await source.departures("Lima", "Cajamarca", DAY) == []
    assert await source.departures("Lima", "Cajamarca", DAY) == []

    queue = RequestQueue(pool)
    assert await queue.claim() == ("bus.example", Query("Lima", "Cajamarca", DAY))
    assert await queue.claim() is None


async def test_a_fresh_read_is_served_and_a_stale_one_queued_again(pool):
    await ResultRepository(pool).store("bus.example", Query("Lima", "Cajamarca", DAY), (DEPARTURE,), NOW - timedelta(minutes=5))

    assert await _source(pool).departures("lima", "cajamarca", DAY) == [DEPARTURE]
    assert await _source(pool, now=NOW + timedelta(minutes=20)).departures("Lima", "Cajamarca", DAY) == []
    assert await RequestQueue(pool).claim() is not None


async def test_routes_the_operator_does_not_serve_cost_nothing(pool):
    assert await _source(pool).departures("Lima", "Arequipa", DAY) == []
    assert await RequestQueue(pool).claim() is None


async def test_a_route_recipe_wins_over_the_operator_wide_one(pool):
    recipes = RecipeRepository(pool)
    wide = Recipe("bus.example", ANY_ROUTE, SITE.start_url, "ready", "", url_template="https://bus.example/{origin_slug}?d={date}")
    own = Recipe("bus.example", "lima>cajamarca", SITE.start_url, "ready", "", steps=(Step("type", text="{origin}"),))
    await recipes.save(wide, SITE.compliance_note)
    await recipes.save(own, SITE.compliance_note)

    assert await recipes.find("bus.example", Query("Lima", "Cajamarca", DAY)) == own
    assert await recipes.find("bus.example", Query("Lima", "Trujillo", DAY)) == wide
