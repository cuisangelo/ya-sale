import asyncio
from datetime import date, datetime

import httpx
from pydantic import BaseModel

from app.departures.domain import LIMA, Departure
from app.flights.domain import airport_of, booking_url
from app.legs.domain import Mode

API_HOST = "aerodatabox.p.rapidapi.com"
# The plan answers at most 12 hours per call, so a day takes two.
HALF_DAYS = (("00:00", "11:59"), ("12:00", "23:59"))
SCHEDULED_PASSENGER_DEPARTURES = {
    "direction": "Departure",
    "withLeg": "true",
    "withCancelled": "false",
    "withCodeshared": "false",
    "withCargo": "false",
    "withPrivate": "false",
}


class _Time(BaseModel):
    local: str  # "2026-10-22 04:50-05:00"


class _Airport(BaseModel):
    iata: str | None = None


class _Movement(BaseModel):
    # The requested airport is left out of its own side of the leg.
    airport: _Airport | None = None
    scheduledTime: _Time | None = None


class _Airline(BaseModel):
    name: str
    iata: str | None = None


class _Flight(BaseModel):
    number: str
    departure: _Movement
    arrival: _Movement
    airline: _Airline


class _Fids(BaseModel):
    departures: list[_Flight] = []


class AeroDataBoxSource:
    """Every airline's scheduled flights from AeroDataBox; it has no fares, so each flight links to its airline's search."""

    seller = "aerodatabox.com"
    mode: Mode = "avion"

    def __init__(self, client: httpx.AsyncClient, api_key: str, pause_s: float):
        self._client = client
        self._api_key = api_key
        self._pause_s = pause_s
        # The free plan allows a few hundred calls a month and schedules barely move within a day.
        self._days: dict[tuple[str, date], list[_Flight]] = {}

    async def departures(self, origin: str, destination: str, travel_date: date) -> list[Departure]:
        origin_code, destination_code = airport_of(origin), airport_of(destination)
        if origin_code is None or destination_code is None:
            return []
        flights = await self._day(origin_code, travel_date)
        return [
            self._departure(flight, origin_code, destination_code, travel_date)
            for flight in flights
            if flight.departure.scheduledTime is not None
            and flight.arrival.airport is not None
            and flight.arrival.airport.iata == destination_code
        ]

    async def _day(self, airport: str, day: date) -> list[_Flight]:
        if (airport, day) not in self._days:
            flights = []
            for position, (start, end) in enumerate(HALF_DAYS):
                if position:
                    await asyncio.sleep(self._pause_s)  # the plan allows one call per second
                flights += await self._half_day(airport, f"{day}T{start}", f"{day}T{end}")
            self._days[(airport, day)] = flights
        return self._days[(airport, day)]

    async def _half_day(self, airport: str, start: str, end: str) -> list[_Flight]:
        response = await self._client.get(
            f"https://{API_HOST}/flights/airports/iata/{airport}/{start}/{end}",
            params=SCHEDULED_PASSENGER_DEPARTURES,
            headers={"X-RapidAPI-Key": self._api_key, "X-RapidAPI-Host": API_HOST},
        )
        response.raise_for_status()
        if response.status_code == 204:
            return []
        return _Fids.model_validate(response.json()).departures

    def _departure(self, flight: _Flight, origin: str, destination: str, day: date) -> Departure:
        return Departure(
            operator=f"{flight.airline.name} {flight.number}",
            departs_at=_lima(flight.departure.scheduledTime),
            arrives_at=_lima(flight.arrival.scheduledTime) if flight.arrival.scheduledTime else None,
            price_pen=None,
            seats_available=None,
            booking_url=booking_url(flight.airline.iata, origin, destination, day),
            seller=self.seller,
        )


def _lima(time: _Time) -> datetime:
    return datetime.fromisoformat(time.local).astimezone(LIMA)
