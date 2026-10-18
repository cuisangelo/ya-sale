import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.connectors.linea import LineaPageChanged, LineaSource
from app.departures.domain import LIMA

FIXTURES = Path(__file__).parent / "fixtures" / "linea"
DAY = date(2026, 10, 22)


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class FakeLinea:
    """Answers like linea.pe did on 17 Oct 2026, keeping the searched route in each visitor's session."""

    def __init__(self, day_lists=None, status=200):
        self.requests: list[httpx.Request] = []
        self._day_lists = day_lists or {("LIMA", "TRUJILLO", "22/10/2026"): fixture("lima-trujillo-2026-10-22.html")}
        self._status = status
        self._sessions: dict[str, tuple[str, str, str]] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._status != 200:
            return httpx.Response(self._status, text="Forbidden")
        path = request.url.path
        if path == "/index.aspx/ListarOrigen":
            return httpx.Response(200, content=fixture("origins.json"))
        if path == "/index.aspx/ListarDestino":
            origin = json.loads(request.content)["objOrigen"]["Origen"]
            return httpx.Response(200, content=fixture("destinations-lima.json") if origin == "LIMA" else b'{"d":[]}')
        if path == "/index.aspx/MostrarItinerario":
            cart = json.loads(request.content)["Carrito"]
            session = request.headers.get("cookie", "").removeprefix("ASP.NET_SessionId=")
            if session not in self._sessions:
                session = f"s{len(self._sessions) + 1}"
                # Like their server: a session keeps the route it searched first.
                self._sessions[session] = (cart["Origen"], cart["Destino"], cart["FechaIda"])
            body = {"d": {"Item1": "1", "Item2": "ECommerce/wf_itinerarioIda.aspx", "Item3": ""}}
            return httpx.Response(200, json=body, headers={"set-cookie": f"ASP.NET_SessionId={session}; path=/"})
        if path == "/ECommerce/wf_ListaItinerarios.aspx":
            session = request.headers.get("cookie", "").removeprefix("ASP.NET_SessionId=")
            if session not in self._sessions:
                return httpx.Response(302, headers={"location": "https://www.linea.pe/error.html"})
            origin, destination, day = self._sessions[session]
            return httpx.Response(200, content=self._day_lists.get((origin, destination, day), fixture("piura-chiclayo-2026-10-22.html")))
        return httpx.Response(404)

    def searches(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path == "/index.aspx/MostrarItinerario"]


def source(fake: FakeLinea) -> LineaSource:
    return LineaSource(lambda: httpx.AsyncClient(transport=httpx.MockTransport(fake)))


def with_trips(edit) -> bytes:
    return edit(fixture("lima-trujillo-2026-10-22.html").decode()).encode()


async def test_each_recorded_trip_becomes_a_departure_with_its_cheapest_seat_and_free_seats():
    departures = await source(FakeLinea()).departures("Lima", "Trujillo", DAY)
    first = departures[0]
    assert first.operator == "Línea · VIP/ESPECIAL"
    assert first.departs_at == datetime(2026, 10, 22, 9, 0, tzinfo=LIMA)
    assert first.arrives_at is None
    assert first.price_pen == Decimal("80")
    assert first.seats_available == 9 + 45
    assert first.booking_url == "https://www.linea.pe/"
    assert first.seller == "linea.pe"
    assert [(d.departs_at.strftime("%H:%M"), d.operator, d.price_pen, d.seats_available) for d in departures] == [
        ("09:00", "Línea · VIP/ESPECIAL", Decimal("80"), 54),
        ("20:00", "Línea · VIP/ESPECIAL EC", Decimal("70"), 52),
        ("20:00", "Línea · SUPER VIP", Decimal("115"), 15),
        ("20:30", "Línea · VIP/ESPECIAL", Decimal("80"), 53),
        ("21:00", "Línea · SUPER VIP", Decimal("115"), 21),
        ("22:00", "Línea · DORADO", Decimal("95"), 24),
        ("22:30", "Línea · VIP/ESPECIAL", Decimal("80"), 49),
    ]


async def test_place_names_are_matched_to_their_terminal_codes():
    fake = FakeLinea()
    await source(fake).departures("LIMA", "trujillo", DAY)
    assert [json.loads(r.content)["Carrito"] for r in fake.searches()] == [
        {"Origen": "LIMA", "Destino": "TRUJILLO", "FechaIda": "22/10/2026", "FechaVuelta": "", "chkPuntos": 0}
    ]


async def test_a_place_they_do_not_serve_finds_nothing_without_searching():
    fake = FakeLinea()
    assert await source(fake).departures("Lima", "Arequipa", DAY) == []
    assert await source(fake).departures("Arequipa", "Lima", DAY) == []
    assert fake.searches() == []


async def test_a_route_they_do_not_run_finds_nothing_without_searching():
    fake = FakeLinea()
    assert await source(fake).departures("Lima", "Piura", DAY) == []
    assert fake.searches() == []


async def test_each_search_starts_its_own_session_so_it_never_reads_another_searchs_route():
    fake = FakeLinea()
    linea = source(fake)
    await linea.departures("Lima", "Trujillo", DAY)
    assert await linea.departures("Lima", "Huaraz", DAY) == []
    assert all("cookie" not in r.headers for r in fake.searches())


async def test_a_day_without_trips_finds_nothing():
    fake = FakeLinea(day_lists={("LIMA", "TRUJILLO", "22/10/2026"): fixture("piura-chiclayo-2026-10-22.html")})
    assert await source(fake).departures("Lima", "Trujillo", DAY) == []


async def test_a_page_without_trips_or_its_empty_notice_raises_instead_of_finding_nothing():
    fake = FakeLinea(day_lists={("LIMA", "TRUJILLO", "22/10/2026"): b"<html><body>Mantenimiento</body></html>"})
    with pytest.raises(LineaPageChanged):
        await source(fake).departures("Lima", "Trujillo", DAY)


async def test_a_trip_without_its_departure_time_raises():
    page = with_trips(lambda html: html.replace(">10:00 pm</h2>", "></h2>"))
    fake = FakeLinea(day_lists={("LIMA", "TRUJILLO", "22/10/2026"): page})
    with pytest.raises(LineaPageChanged):
        await source(fake).departures("Lima", "Trujillo", DAY)


async def test_a_lost_session_raises():
    class LosesSessions(FakeLinea):
        def __call__(self, request):
            response = super().__call__(request)
            response.headers.pop("set-cookie", None)
            return response

    with pytest.raises(httpx.HTTPStatusError):
        await source(LosesSessions()).departures("Lima", "Trujillo", DAY)


async def test_a_blocked_request_raises():
    with pytest.raises(httpx.HTTPStatusError):
        await source(FakeLinea(status=403)).departures("Lima", "Trujillo", DAY)


async def test_origins_are_fetched_once_per_instance():
    fake = FakeLinea()
    linea = source(fake)
    await linea.departures("Lima", "Trujillo", DAY)
    await linea.departures("Lima", "Trujillo", DAY)
    assert sum(r.url.path == "/index.aspx/ListarOrigen" for r in fake.requests) == 1
