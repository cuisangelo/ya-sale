from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.connectors.ittsa import ROUTES_URL, IttsaPageChanged, IttsaSource
from app.departures.domain import LIMA

FIXTURES = Path(__file__).parent / "fixtures" / "ittsa"
DAY = date(2026, 10, 22)
DAY_PAGE = "https://www.ittsabus.com/online/programacion/?origenId=3&destinoId=10&fechaIda=2026-10-22&trip=oneway"
LIMA_TRUJILLO = "origenId=3&destinoId=10&fechaIda=2026-10-22"


def page(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text()


class FakeIttsa:
    """Answers like ittsabus.com did on 17 Oct 2026."""

    def __init__(self, pages=None, status=200):
        self.requests: list[httpx.Request] = []
        self._pages = pages or {LIMA_TRUJILLO: page("lima-trujillo-2026-10-22")}
        self._status = status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._status != 200:
            return httpx.Response(self._status, text="Forbidden")
        if str(request.url) == ROUTES_URL:
            return httpx.Response(200, text=page("online"))
        query = request.url.query.decode().removesuffix("&trip=oneway")
        if request.url.path == "/online/programacion/" and query in self._pages:
            return httpx.Response(200, text=self._pages[query])
        return httpx.Response(404)

    def day_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path == "/online/programacion/"]


def source(fake: FakeIttsa) -> IttsaSource:
    return IttsaSource(httpx.AsyncClient(transport=httpx.MockTransport(fake)))


async def test_each_recorded_trip_becomes_a_departure_linked_to_that_days_list():
    departures = await source(FakeIttsa()).departures("Lima", "Trujillo", DAY)
    first = departures[0]
    assert first.operator == "ITTSA · MIXTO 56"
    assert first.departs_at == datetime(2026, 10, 22, 8, 0, tzinfo=LIMA)
    assert first.arrives_at == datetime(2026, 10, 22, 18, 0, tzinfo=LIMA)
    assert first.booking_url == DAY_PAGE
    assert first.seller == "ittsabus.com"
    assert [(d.departs_at.strftime("%H:%M"), d.price_pen, d.seats_available) for d in departures] == [
        ("08:00", Decimal("80"), 55),
        ("12:00", Decimal("80"), 53),
        ("20:00", Decimal("85"), 54),
        ("20:15", Decimal("110"), 23),
        ("21:10", Decimal("85"), 37),
        ("21:30", Decimal("110"), 24),
        ("21:45", Decimal("85"), 53),
        ("22:00", Decimal("110"), 16),
        ("22:10", Decimal("110"), 24),
        ("23:00", Decimal("110"), 27),
        ("23:15", Decimal("85"), 54),
    ]


async def test_an_overnight_trip_arrives_the_next_day():
    departures = await source(FakeIttsa()).departures("Lima", "Trujillo", DAY)
    assert departures[2].arrives_at == datetime(2026, 10, 23, 6, 0, tzinfo=LIMA)


async def test_a_city_is_matched_to_its_first_terminal_on_their_route_list():
    fake = FakeIttsa()
    await source(fake).departures("LIMA", "Trujillo", DAY)
    assert [str(r.url) for r in fake.day_requests()] == [DAY_PAGE]


async def test_a_place_they_do_not_serve_finds_nothing_without_loading_a_day():
    fake = FakeIttsa()
    assert await source(fake).departures("Lima", "Barranca", DAY) == []
    assert fake.day_requests() == []


async def test_two_cities_they_serve_without_a_route_between_them_find_nothing():
    fake = FakeIttsa()
    assert await source(fake).departures("Lambayeque", "Tumbes", DAY) == []
    assert fake.day_requests() == []


async def test_a_day_without_trips_finds_nothing():
    fake = FakeIttsa(pages={"origenId=3&destinoId=1&fechaIda=2027-03-15": page("lima-chiclayo-2027-03-15")})
    assert await source(fake).departures("Lima", "Chiclayo", date(2027, 3, 15)) == []


async def test_trips_that_leave_another_day_are_dropped():
    after_midnight = page("lima-trujillo-2026-10-22").replace(
        '\\"feSalidaPlanificada\\":\\"2026-10-22 08:00:00\\"', '\\"feSalidaPlanificada\\":\\"2026-10-23 00:30:00\\"'
    )
    departures = await source(FakeIttsa(pages={LIMA_TRUJILLO: after_midnight})).departures("Lima", "Trujillo", DAY)
    assert len(departures) == 10


@pytest.mark.parametrize(
    ("floor_prices", "price"),
    [(("0", "80"), Decimal("80")), (("0", "0"), None)],
)
async def test_a_floor_priced_at_zero_is_not_a_price(floor_prices, price):
    first, second = floor_prices
    unpriced = page("lima-trujillo-2026-10-22").replace(
        '\\"precioMinimoPiso1\\":110,\\"precioMinimoPiso2\\":80,', f'\\"precioMinimoPiso1\\":{first},\\"precioMinimoPiso2\\":{second},', 1
    )
    departures = await source(FakeIttsa(pages={LIMA_TRUJILLO: unpriced})).departures("Lima", "Trujillo", DAY)
    assert departures[0].price_pen == price


async def test_a_page_without_its_data_raises_instead_of_finding_nothing():
    fake = FakeIttsa(pages={LIMA_TRUJILLO: "<html><body>Mantenimiento</body></html>"})
    with pytest.raises(IttsaPageChanged):
        await source(fake).departures("Lima", "Trujillo", DAY)


async def test_a_blocked_request_raises():
    with pytest.raises(httpx.HTTPStatusError):
        await source(FakeIttsa(status=403)).departures("Lima", "Trujillo", DAY)


async def test_routes_are_fetched_once_per_instance():
    fake = FakeIttsa()
    ittsa = source(fake)
    await ittsa.departures("Lima", "Trujillo", DAY)
    await ittsa.departures("Lima", "Trujillo", DAY)
    assert sum(str(r.url) == ROUTES_URL for r in fake.requests) == 1
