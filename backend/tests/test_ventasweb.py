import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.connectors.ventasweb import VentasWebSearchFailed, VentasWebSource
from app.departures.domain import LIMA

FIXTURES = Path(__file__).parent / "fixtures"
DAY = date(2026, 10, 20)
DAY_PAGE = "https://sales.ghbus.com.pe/?idorigen=1&iddestino=2&fechaida=20/10/2026"


def fixture(name: str, site: str = "ghbus") -> str:
    return (FIXTURES / site / f"{name}.json").read_text()


def with_first_trip(**changes) -> str:
    answer = json.loads(fixture("lima-chiclayo-2026-10-20"))
    answer["datos"][0].update(changes)
    return json.dumps(answer)


class FakeVentasWeb:
    """Answers like sales.ghbus.com.pe (or another site on the platform) did on 18 Oct 2026, one session per client."""

    def __init__(self, searches=None, site="ghbus"):
        self.requests: list[httpx.Request] = []
        self.sessions_opened = 0
        self._site = site
        self._searches = searches or {(1, 2, "20/10/2026"): fixture("lima-chiclayo-2026-10-20")}

    def session(self) -> httpx.AsyncClient:
        self.sessions_opened += 1
        return httpx.AsyncClient(transport=httpx.MockTransport(self))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/api/base/lista-oficinas":
            return httpx.Response(200, text=fixture("oficinas", self._site))
        if request.method == "GET" and request.url.path == "/":
            return httpx.Response(200, text="<html>Sistema de Ventas Web - GH BUS S.A.C.</html>")
        if request.method == "POST" and request.url.path == "/busqueda-turnos":
            body = json.loads(request.content)
            answer = self._searches.get((body["CodiOrigen"], body["CodiDestino"], body["FechaViaje"]), fixture("no-trips"))
            return httpx.Response(200, text=answer)
        return httpx.Response(404)

    def searches(self) -> list[dict]:
        return [json.loads(r.content) for r in self.requests if r.url.path == "/busqueda-turnos"]


def source(fake: "FakeVentasWeb") -> VentasWebSource:
    return VentasWebSource("https://sales.ghbus.com.pe", "ghbus.com.pe", "GH Bus", fake.session)


def flores(fake: "FakeVentasWeb") -> VentasWebSource:
    return VentasWebSource("https://sales.floreshnos.pe", "floreshnos.pe", "Flores", fake.session)


async def test_each_recorded_trip_becomes_a_departure_linked_to_that_days_search():
    [departure] = await source(FakeVentasWeb()).departures("Lima", "Chiclayo", DAY)
    assert departure.operator == "GH Bus · COMFORT CLASS"
    assert departure.departs_at == datetime(2026, 10, 20, 15, 0, tzinfo=LIMA)
    assert departure.price_pen == Decimal("70")
    assert departure.seats_available == 48
    assert departure.booking_url == DAY_PAGE
    assert departure.seller == "ghbus.com.pe"


async def test_their_arrival_is_a_placeholder_so_it_is_left_unknown():
    [departure] = await source(FakeVentasWeb()).departures("Lima", "Chiclayo", DAY)
    assert departure.arrives_at is None


async def test_the_search_runs_after_opening_its_page_in_the_same_session():
    fake = FakeVentasWeb()
    await source(fake).departures("Lima", "Chiclayo", DAY)
    page = next(i for i, r in enumerate(fake.requests) if str(r.url) == DAY_PAGE)
    search = next(i for i, r in enumerate(fake.requests) if r.url.path == "/busqueda-turnos")
    assert page < search
    assert fake.searches() == [{"CodiOrigen": 1, "CodiDestino": 2, "FechaViaje": "20/10/2026", "SoloProgramados": False}]


async def test_a_city_named_with_its_district_is_matched_by_its_city():
    fake = FakeVentasWeb()
    await source(fake).departures("Lima", "Tarapoto", DAY)
    assert fake.searches()[0]["CodiDestino"] == 9


async def test_a_place_they_do_not_serve_finds_nothing_without_searching():
    fake = FakeVentasWeb()
    assert await source(fake).departures("Lima", "Cusco", DAY) == []
    assert fake.searches() == []


async def test_a_day_without_trips_finds_nothing():
    assert await source(FakeVentasWeb()).departures("Lima", "Tarapoto", DAY) == []


@pytest.mark.parametrize(("floor_prices", "price"), [((0, 70), Decimal("70")), ((0, 0), None)])
async def test_a_floor_priced_at_zero_is_not_a_price(floor_prices, price):
    first, second = floor_prices
    fake = FakeVentasWeb(searches={(1, 2, "20/10/2026"): with_first_trip(precio_N1=first, precio_N2=second)})
    [departure] = await source(fake).departures("Lima", "Chiclayo", DAY)
    assert departure.price_pen == price


async def test_trips_that_leave_another_day_are_dropped():
    fake = FakeVentasWeb(searches={(1, 2, "20/10/2026"): with_first_trip(fechaViaje="21/10/2026")})
    assert await source(fake).departures("Lima", "Chiclayo", DAY) == []


async def test_a_failed_search_raises_instead_of_finding_nothing():
    fake = FakeVentasWeb(searches={(1, 2, "20/10/2026"): fixture("failed")})
    with pytest.raises(VentasWebSearchFailed):
        await source(fake).departures("Lima", "Chiclayo", DAY)


async def test_every_search_opens_its_own_session_and_offices_are_fetched_once():
    fake = FakeVentasWeb()
    gh = source(fake)
    await gh.departures("Lima", "Chiclayo", DAY)
    await gh.departures("Lima", "Chiclayo", DAY)
    assert fake.sessions_opened == 2
    assert sum(r.url.path == "/api/base/lista-oficinas" for r in fake.requests) == 1


async def test_another_operator_on_the_platform_gets_its_own_seller_link_and_arrival():
    fake = FakeVentasWeb(
        searches={(6, 7, "19/10/2026"): fixture("lima-cajamarca-2026-10-19", "flores")}, site="flores"
    )
    [departure] = await flores(fake).departures("Lima", "Cajamarca", date(2026, 10, 19))
    assert departure.operator == "Flores · BUS CAMA"
    assert departure.departs_at == datetime(2026, 10, 19, 17, 30, tzinfo=LIMA)
    assert departure.arrives_at == datetime(2026, 10, 20, 8, 30, tzinfo=LIMA)
    assert departure.price_pen == Decimal("70")
    assert departure.seats_available == 46
    assert departure.booking_url == "https://sales.floreshnos.pe/?idorigen=6&iddestino=7&fechaida=19/10/2026"
    assert departure.seller == "floreshnos.pe"
