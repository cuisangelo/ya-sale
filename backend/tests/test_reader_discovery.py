from datetime import date
from itertools import count
from types import SimpleNamespace

from app.reader.discovery import Discoverer
from app.reader.domain import ANY_ROUTE, Query
from app.reader.replay import replay

QUERY = Query("Lima", "Cajamarca", date(2026, 10, 20))
HOME = "https://bus.example/"
_ids = count()


def _call(name: str, args: dict, toolset: str | None = "computer"):
    return SimpleNamespace(type="tool_use", id=f"toolu_{next(_ids)}", name=name, input=args, toolset_name=toolset)


def _response(*blocks, stop_reason="tool_use"):
    usage = SimpleNamespace(input_tokens=100, output_tokens=20, cache_read_input_tokens=0, cache_creation_input_tokens=0)
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason, usage=usage)


class FakeClient:
    def __init__(self, *responses):
        self._responses = list(responses)
        self.requests: list[dict] = []
        self.messages = self

    async def create(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})
        return self._responses.pop(0)


class FakeScreen:
    """A search form whose Buscar button leads to a results URL that carries the route and date."""

    def __init__(self):
        self.url = ""
        self.typed: list[str] = []
        self.clicked_labels: list[str] = []

    async def open(self, url):
        self.url = url

    async def settle(self):
        pass

    async def screenshot(self):
        return b"png"

    async def element_at(self, x, y):
        return ("form > button", "Buscar") if (x, y) == (900, 100) else ("#origin", None)

    async def click(self, x, y, count=1):
        if (x, y) == (900, 100):
            self.url = f"{HOME}pasajes/lima/cajamarca?fecha=20-10-2026"

    async def click_selector(self, selector):
        return False

    async def click_label(self, label):
        self.clicked_labels.append(label)
        return True

    async def move(self, x, y):
        pass

    async def type(self, text):
        self.typed.append(text)

    async def key(self, combo, repeat=1):
        pass

    async def scroll(self, direction, amount, x, y):
        pass

    async def wait(self, seconds):
        pass

    async def text(self):
        return "16:00 S/70"


async def test_discovery_turns_the_visitor_path_into_a_replayable_url_template():
    client = FakeClient(
        _response(_call("left_click", {"coordinate": [100, 100]}), _call("type", {"text": "Lima"})),
        _response(_call("left_click", {"coordinate": [900, 100]})),
        _response(_call("finish", {"outcome": "results", "note": "list shown"}, toolset=None)),
    )
    screen = FakeScreen()

    found = await Discoverer(client).discover(screen, "bus.example", HOME, QUERY)

    assert (found.outcome, found.actions, found.usage.calls) == ("results", 3, 3)
    assert found.recipe.route_key == ANY_ROUTE
    assert found.recipe.url_template == f"{HOME}pasajes/{{origin_slug}}/{{destination_slug}}?fecha={{date_dmy_dash}}"
    assert found.recipe.submit_label == "Buscar"
    # Every result echoes the toolset, or the API rejects the turn.
    results = client.requests[1]["messages"][-1]["content"]
    assert [r["toolset_name"] for r in results] == ["computer", "computer"]

    replayed = await replay(FakeScreen(), found.recipe, Query("Trujillo", "Jaén", date(2026, 10, 25)))
    assert replayed.url == f"{HOME}pasajes/trujillo/jaen?fecha=25-10-2026"


async def test_typing_anything_but_the_trip_is_refused_and_the_rest_of_the_turn_skipped():
    client = FakeClient(
        _response(_call("type", {"text": "juan@example.com"}), _call("left_click", {"coordinate": [900, 100]})),
        _response(_call("finish", {"outcome": "unavailable", "note": "no search"}, toolset=None)),
    )
    screen = FakeScreen()

    found = await Discoverer(client).discover(screen, "bus.example", HOME, QUERY)

    assert screen.typed == []
    assert screen.url == HOME
    refused, skipped = client.requests[1]["messages"][-1]["content"]
    assert refused["is_error"] and "limited to the trip" in refused["content"]
    assert skipped["is_error"] and skipped["content"].startswith("Not executed")
    assert (found.outcome, found.recipe) == ("unavailable", None)


async def test_a_challenge_is_recorded_as_blocked_for_the_whole_operator():
    client = FakeClient(_response(_call("finish", {"outcome": "blocked", "note": "captcha"}, toolset=None)))

    found = await Discoverer(client).discover(FakeScreen(), "bus.example", HOME, QUERY)

    assert found.outcome == "blocked"
    assert (found.recipe.status, found.recipe.route_key) == ("blocked", ANY_ROUTE)


async def test_discovery_gives_up_after_its_action_budget():
    client = FakeClient(*[_response(_call("scroll", {"scroll_direction": "down", "scroll_amount": 3})) for _ in range(30)])

    found = await Discoverer(client).discover(FakeScreen(), "bus.example", HOME, QUERY)

    assert (found.outcome, found.actions, found.recipe) == ("gave_up", 25, None)
