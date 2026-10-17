from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Protocol

# Peru has no daylight saving time, so a fixed offset is exact and needs no tz database.
LIMA = timezone(timedelta(hours=-5), "America/Lima")


@dataclass(frozen=True)
class Departure:
    """One concrete bus departure on sale, linked to the page where its seat is picked."""

    operator: str
    departs_at: datetime
    arrives_at: datetime | None
    price_pen: Decimal | None
    seats_available: int | None
    booking_url: str
    seller: str


class DepartureSource(Protocol):
    seller: str

    async def departures(self, origin: str, destination: str, travel_date: date) -> list[Departure]: ...


def by_departure_time(found: Iterable[Iterable[Departure]]) -> tuple[Departure, ...]:
    return tuple(sorted((d for departures in found for d in departures), key=lambda d: d.departs_at))
