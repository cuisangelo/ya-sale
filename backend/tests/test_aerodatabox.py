from datetime import date, datetime
from pathlib import Path

import httpx
import pytest

from app.connectors.aerodatabox import AeroDataBoxSource
from app.departures.domain import LIMA

FIXTURES = Path(__file__).parent / "fixtures" / "aerodatabox"
DAY = date(2026, 10, 22)
HALF_DAYS = {
    "/flights/airports/iata/LIM/2026-10-22T00:00/2026-10-22T11:59": "LIM_2026-10-22_am.json",
    "/flights/airports/iata/LIM/2026-10-22T12:00/2026-10-22T23:59": "LIM_2026-10-22_pm.json",
}


class FakeAeroDataBox:
    """Answers the airport departures endpoint with the recorded Lima departures of 22 Oct 2026."""

    def __init__(self, status=200, empty=False):
        self.requests: list[httpx.Request] = []
        self._status = status
        self._empty = empty

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._status != 200:
            return httpx.Response(self._status, json={"message": "You have exceeded the rate limit per second for your plan"})
        if self._empty:
            return httpx.Response(204)
        fixture = HALF_DAYS.get(request.url.path)
        return httpx.Response(200, content=(FIXTURES / fixture).read_bytes()) if fixture else httpx.Response(404)


def source(fake: FakeAeroDataBox) -> AeroDataBoxSource:
    return AeroDataBoxSource(httpx.AsyncClient(transport=httpx.MockTransport(fake)), api_key="test-key", pause_s=0)


async def test_every_flight_to_the_destination_that_day_becomes_a_departure():
    departures = await source(FakeAeroDataBox()).departures("Lima", "Cusco", DAY)
    assert [(d.operator, d.departs_at.strftime("%H:%M")) for d in departures] == [
        ("Sky Airline Peru H2 5001", "04:50"),
        ("JetSMART JA 7005", "08:05"),
        ("LATAM LA 2029", "19:15"),
    ]
    sky = departures[0]
    assert sky.departs_at == datetime(2026, 10, 22, 4, 50, tzinfo=LIMA)
    assert sky.arrives_at == datetime(2026, 10, 22, 6, 15, tzinfo=LIMA)
    assert sky.price_pen is None and sky.seats_available is None
    assert sky.seller == "aerodatabox.com"


async def test_a_flight_without_a_scheduled_arrival_keeps_its_departure():
    departures = await source(FakeAeroDataBox()).departures("Lima", "Cusco", DAY)
    assert departures[1].arrives_at is None


async def test_each_flight_links_to_its_airlines_search_for_that_day():
    departures = await source(FakeAeroDataBox()).departures("Lima", "Cusco", DAY)
    assert departures[0].booking_url == (
        "https://initial-sale.skyairline.com/es/peru?origin=LIM&destination=CUZ"
        "&departureDate=2026-10-22&arrivalDate=2026-10-22&flightType=OW&ADT=1"
    )
    tarapoto = await source(FakeAeroDataBox()).departures("Lima", "Tarapoto", DAY)
    assert tarapoto[0].booking_url == (
        "https://www.starperu.com/Booking1?tipo_viaje=O&origen=LIM&destino=TPP&from=22%2F10%2F2026"
        "&to=22%2F10%2F2026&cant_adultos=1&cant_ninos=0&cant_infantes=0&codigo_desc="
    )


async def test_an_airline_without_a_dated_search_link_opens_google_flights_for_that_day():
    departures = await source(FakeAeroDataBox()).departures("Lima", "Cusco", DAY)
    assert departures[2].booking_url == "https://www.google.com/travel/flights?q=Flights+from+LIM+to+CUZ+on+2026-10-22+one+way"


async def test_the_day_is_asked_in_two_half_days_of_scheduled_passenger_departures_only():
    fake = FakeAeroDataBox()
    await source(fake).departures("Lima", "Cusco", DAY)
    assert sorted(r.url.path for r in fake.requests) == sorted(HALF_DAYS)
    params = dict(fake.requests[0].url.params)
    assert params == {
        "direction": "Departure",
        "withLeg": "true",
        "withCancelled": "false",
        "withCodeshared": "false",
        "withCargo": "false",
        "withPrivate": "false",
    }
    assert fake.requests[0].headers["X-RapidAPI-Key"] == "test-key"
    assert fake.requests[0].headers["X-RapidAPI-Host"] == "aerodatabox.p.rapidapi.com"


async def test_a_second_trip_from_the_same_airport_and_day_reuses_the_first_answer():
    fake = FakeAeroDataBox()
    adb = source(fake)
    await adb.departures("Lima", "Cusco", DAY)
    tarapoto = await adb.departures("Lima", "Tarapoto", DAY)
    assert len(fake.requests) == 2
    assert [d.operator for d in tarapoto] == ["Star Peru 2I 3143"]


async def test_city_names_match_their_airport_ignoring_case_and_accents():
    fake = FakeAeroDataBox()
    assert len(await source(fake).departures("LIMA", "Cuzco", DAY)) == 3


async def test_a_city_without_an_airport_finds_nothing_without_calling_the_api():
    fake = FakeAeroDataBox()
    assert await source(fake).departures("Lima", "Sauce", DAY) == []
    assert await source(fake).departures("Huaraz", "Lima", DAY) == []
    assert fake.requests == []


async def test_a_day_without_flights_finds_nothing():
    assert await source(FakeAeroDataBox(empty=True)).departures("Lima", "Cusco", DAY) == []


async def test_a_refused_call_raises_instead_of_finding_nothing():
    with pytest.raises(httpx.HTTPStatusError):
        await source(FakeAeroDataBox(status=429)).departures("Lima", "Cusco", DAY)
