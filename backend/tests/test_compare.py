from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.compare.service import CompareService
from app.legs.domain import LegData, LegVersion
from app.trips.events import LegRefreshed, TripDone, TripStarted

Q = "Quiero ir de Lima a Sauce sin tour, salgo el 25. ¿Cómo llego?"


def version(confirmations=0, version_id=1):
    data = LegData("Paradero", None, Decimal(10), Decimal(15), 90, None, None)
    return LegVersion(version_id, data, "https://a.pe", datetime.now(UTC), confirmations)


class FakePlanner:
    def __init__(self, legs):
        self._legs = legs
        self.calls = []

    async def plan(self, origin, destination, date, trip_id):
        self.calls.append((origin, destination, date))
        yield TripStarted(trip_id, origin, destination, len(self._legs), ())
        for event in self._legs:
            yield event
        yield TripDone(len(self._legs))


TWO_LEGS_ONE_CONFIRMED = [
    LegRefreshed(0, 1, "bus", "Lima", "Tarapoto", "extracted", version(), ()),
    LegRefreshed(1, 2, "colectivo", "Tarapoto", "Sauce", "confirmed", version(confirmations=1, version_id=2), ()),
]


def text_response(text):
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def tool_response():
    block = SimpleNamespace(type="tool_use", id="tu_1", name="plan_trip", input={"origin": "Lima", "destination": "Sauce", "date": "2026-10-25"})
    return SimpleNamespace(stop_reason="tool_use", content=[block])


class FakeClient:
    def __init__(self):
        self.messages = self
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if not kwargs.get("tools"):
            return text_response("Toma un bus a Tarapoto y luego un colectivo.")
        if len(kwargs["messages"]) == 1:
            return tool_response()
        return text_response("Con Ya Sale: bus Lima → Tarapoto y colectivo a Sauce.")


async def test_plain_side_gets_no_tools():
    client = FakeClient()
    await CompareService(client, FakePlanner(TWO_LEGS_ONE_CONFIRMED)).compare(Q)
    plain_calls = [c for c in client.calls if not c.get("tools")]
    assert len(plain_calls) == 1


async def test_both_sides_use_the_same_model():
    client = FakeClient()
    await CompareService(client, FakePlanner(TWO_LEGS_ONE_CONFIRMED)).compare(Q)
    assert {c["model"] for c in client.calls} == {"claude-sonnet-5-5"}


async def test_with_tools_counts_come_from_legs_not_text():
    result = await CompareService(FakeClient(), FakePlanner(TWO_LEGS_ONE_CONFIRMED)).compare(Q)
    assert (result.with_tools.sources, result.with_tools.dated, result.with_tools.confirmed) == (2, 2, 1)
    assert (result.plain.sources, result.plain.dated, result.plain.confirmed) == (0, 0, 0)
    assert len(result.legs) == 2


async def test_tool_result_is_sent_back_to_the_model():
    client = FakeClient()
    planner = FakePlanner(TWO_LEGS_ONE_CONFIRMED)
    result = await CompareService(client, planner).compare(Q)
    assert planner.calls == [("Lima", "Sauce", "2026-10-25")]
    last_user = client.calls[-1]["messages"][-1]
    assert last_user["content"][0]["type"] == "tool_result"
    assert result.with_tools.text.startswith("Con Ya Sale")
