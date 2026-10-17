import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.connectors.oltursa import CITIES_URL, OltursaPageChanged, OltursaSource
from app.departures.domain import LIMA

FIXTURES = Path(__file__).parent / "fixtures" / "oltursa"
DAY = date(2026, 10, 22)
DAY_PAGE = "https://www.oltursa.pe/es/viajes/lima/trujillo/2026-10-22"


def page(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text()


def with_trips(edit) -> str:
    """The recorded Lima -> Trujillo page with its trips changed by `edit`."""
    html = page("lima-trujillo-2026-10-22")
    match = re.search(r'(<script id="__NEXT_DATA__" type="application/json">)(.*?)(</script>)', html, re.S)
    data = json.loads(match.group(2))
    edit(data["props"]["pageProps"]["routeInfo"]["outboundTrips"])
    return html[: match.start(2)] + json.dumps(data) + html[match.end(2):]


class FakeOltursa:
    """Answers like oltursa.pe did on 17 Oct 2026."""

    def __init__(self, pages=None, status=200):
        self.requests: list[httpx.Request] = []
        self._pages = pages or {"/es/viajes/lima/trujillo/2026-10-22": page("lima-trujillo-2026-10-22")}
        self._status = status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._status != 200:
            return httpx.Response(self._status, text="Forbidden")
        if str(request.url) == CITIES_URL:
            return httpx.Response(200, content=(FIXTURES / "cities.json").read_bytes())
        if request.url.path in self._pages:
            return httpx.Response(200, text=self._pages[request.url.path])
        return httpx.Response(404)

    def page_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.host == "www.oltursa.pe"]


def source(fake: FakeOltursa) -> OltursaSource:
    return OltursaSource(httpx.AsyncClient(transport=httpx.MockTransport(fake)))


async def test_each_recorded_trip_becomes_a_departure_linked_to_that_days_list():
    departures = await source(FakeOltursa()).departures("Lima", "Trujillo", DAY)
    first = departures[0]
    assert first.operator == "Oltursa · V.RELAX 180"
    assert first.departs_at == datetime(2026, 10, 22, 10, 0, tzinfo=LIMA)
    assert first.arrives_at == datetime(2026, 10, 22, 21, 30, tzinfo=LIMA)
    assert first.price_pen == Decimal("80")
    assert first.seats_available == 30
    assert first.booking_url == DAY_PAGE
    assert first.seller == "oltursa.pe"
    assert [(d.departs_at.strftime("%H:%M"), d.price_pen, d.seats_available) for d in departures] == [
        ("10:00", Decimal("80"), 30),
        ("11:15", Decimal("80"), 30),
        ("20:45", Decimal("115"), 39),
        ("21:15", Decimal("115"), 39),
        ("22:00", Decimal("115"), 28),
        ("22:30", Decimal("115"), 29),
        ("22:30", Decimal("115"), 39),
    ]


async def test_an_overnight_trip_arrives_the_next_day():
    departures = await source(FakeOltursa()).departures("Lima", "Trujillo", DAY)
    assert departures[2].arrives_at == datetime(2026, 10, 23, 9, 15, tzinfo=LIMA)


async def test_an_arrival_after_new_year_lands_in_the_next_year():
    def new_years_eve(trips):
        trips[0].update(fecha_salida="2026-12-31 22:00:00.0", fllegada_programada="01/01", hllegada_programada="09:15")

    fake = FakeOltursa(pages={"/es/viajes/lima/trujillo/2026-12-31": with_trips(new_years_eve)})
    departures = await source(fake).departures("Lima", "Trujillo", date(2026, 12, 31))
    assert departures[0].arrives_at == datetime(2027, 1, 1, 9, 15, tzinfo=LIMA)


async def test_place_names_are_matched_to_their_slugs():
    fake = FakeOltursa()
    await source(fake).departures("LIMA", "Trujillo", DAY)
    assert [str(r.url) for r in fake.page_requests()] == [DAY_PAGE]


async def test_a_place_they_do_not_serve_finds_nothing_without_loading_a_page():
    fake = FakeOltursa()
    assert await source(fake).departures("Lima", "Barranca", DAY) == []
    assert fake.page_requests() == []


async def test_a_route_without_trips_finds_nothing():
    fake = FakeOltursa(pages={"/es/viajes/tumbes/tacna/2026-10-22": page("tumbes-tacna-2026-10-22")})
    assert await source(fake).departures("Tumbes", "Tacna", DAY) == []


async def test_trips_that_leave_another_day_are_dropped():
    def one_after_midnight(trips):
        trips[0]["fecha_salida"] = "2026-10-23 00:30:00.0"

    fake = FakeOltursa(pages={"/es/viajes/lima/trujillo/2026-10-22": with_trips(one_after_midnight)})
    departures = await source(fake).departures("Lima", "Trujillo", DAY)
    assert len(departures) == 6


async def test_a_page_without_its_data_raises_instead_of_finding_nothing():
    fake = FakeOltursa(pages={"/es/viajes/lima/trujillo/2026-10-22": "<html><body>Mantenimiento</body></html>"})
    with pytest.raises(OltursaPageChanged):
        await source(fake).departures("Lima", "Trujillo", DAY)


async def test_a_blocked_request_raises():
    with pytest.raises(httpx.HTTPStatusError):
        await source(FakeOltursa(status=403)).departures("Lima", "Trujillo", DAY)


async def test_cities_are_fetched_once_per_instance():
    fake = FakeOltursa()
    olt = source(fake)
    await olt.departures("Lima", "Trujillo", DAY)
    await olt.departures("Lima", "Trujillo", DAY)
    assert sum(str(r.url) == CITIES_URL for r in fake.requests) == 1
