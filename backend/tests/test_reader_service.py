from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from app.reader.discovery import Discovery
from app.reader.domain import ANY_ROUTE, OperatorSite, Query, Recipe, Step
from app.reader.extraction import Extraction
from app.reader.service import ReaderService
from app.reader.usage import Usage

QUERY = Query("Lima", "Huancayo", date(2026, 10, 20))
SITE = OperatorSite("bus.example", "Bus Example", "https://bus.example/", frozenset({"lima", "huancayo"}), "robots allows /")
TEMPLATE = Recipe(
    "bus.example", ANY_ROUTE, SITE.start_url, "ready", "", url_template="https://bus.example/paso1/{origin_slug}/{date}",
    steps=(Step("type", text="{origin}"), Step("click", selector=None, x=900, y=100, label="BUSCAR")),
)


class Screen:
    """A site whose results URL only works inside the session that searched: a fresh visitor lands on the home page."""

    def __init__(self):
        self.url, self.page = "", ""

    async def open(self, url):
        self.url, self.page = SITE.start_url, "home"

    async def settle(self):
        pass

    async def click(self, x, y, count=1):
        self.page = "departures list"

    async def click_selector(self, selector):
        return False

    async def click_label(self, label):
        return False

    async def type(self, text):
        pass

    async def key(self, combo, repeat=1):
        pass

    async def scroll(self, direction, amount, x, y):
        pass

    async def text(self):
        return self.page


class Recipes:
    def __init__(self, *recipes):
        self.saved = {r.route_key: r for r in recipes}
        self.forgotten = []

    async def find(self, domain, query):
        return self.saved.get(query.route_key) or self.saved.get(ANY_ROUTE)

    async def save(self, recipe, note):
        self.saved[recipe.route_key] = recipe

    async def forget(self, recipe):
        self.forgotten.append(recipe)
        self.saved.pop(recipe.route_key)


class Results:
    async def store(self, domain, query, departures, read_at):
        self.stored = departures


class Extractor:
    async def extract(self, page_text, *args):
        return Extraction("departures" if "list" in page_text else "not_results", (), Usage(calls=1))


class Discoverer:
    def __init__(self, found: Discovery):
        self.found, self.calls = found, 0

    async def discover(self, screen, domain, start_url, query):
        self.calls += 1
        return self.found


@asynccontextmanager
async def _tab():
    yield Screen()


def _service(recipes, discoverer):
    return ReaderService(recipes, Results(), discoverer, Extractor(), _tab, clock=lambda: datetime.now(timezone.utc))


async def test_a_session_bound_results_url_falls_back_to_the_recorded_clicks_for_that_route():
    recipes = Recipes(TEMPLATE)
    discoverer = Discoverer(Discovery("results", "", TEMPLATE, 3, Usage()))

    found = await _service(recipes, discoverer).read(SITE, QUERY)

    assert (found.status, found.discovered, discoverer.calls) == ("departures", False, 0)
    route_recipe = recipes.saved[QUERY.route_key]
    assert route_recipe.url_template is None and route_recipe.steps == TEMPLATE.steps


async def test_a_blocked_operator_is_never_driven_again():
    discoverer = Discoverer(Discovery("results", "", TEMPLATE, 3, Usage()))
    blocked = Recipe("bus.example", ANY_ROUTE, SITE.start_url, "blocked", "captcha")

    found = await _service(Recipes(blocked), discoverer).read(SITE, QUERY)

    assert (found.status, discoverer.calls) == ("blocked", 0)


async def test_a_stale_recipe_is_forgotten_and_rediscovered_once():
    stale = Recipe("bus.example", ANY_ROUTE, SITE.start_url, "ready", "", url_template="https://bus.example/old/{date}")
    recipes = Recipes(stale)
    discoverer = Discoverer(Discovery("gave_up", "no list", None, 25, Usage(calls=9)))

    found = await _service(recipes, discoverer).read(SITE, QUERY)

    assert recipes.forgotten == [stale]
    assert (found.status, found.discovered, discoverer.calls, found.usage.calls) == ("unreadable", True, 1, 10)
