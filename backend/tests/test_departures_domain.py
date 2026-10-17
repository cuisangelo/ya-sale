from datetime import datetime
from decimal import Decimal

from app.departures.domain import LIMA, Departure, by_departure_time


def departure(hour: int, operator: str = "Movil Bus") -> Departure:
    return Departure(
        operator=operator,
        departs_at=datetime(2026, 10, 25, hour, 30, tzinfo=LIMA),
        arrives_at=None,
        price_pen=Decimal("35"),
        seats_available=12,
        booking_url=f"https://vendedor.pe/salida/{hour}",
        seller="vendedor.pe",
    )


def test_departures_from_every_source_are_merged_earliest_first():
    merged = by_departure_time([[departure(19), departure(7)], [departure(13, "Civa")]])
    assert [d.departs_at.hour for d in merged] == [7, 13, 19]


def test_lima_time_is_utc_minus_five():
    assert departure(19).departs_at.utcoffset().total_seconds() == -5 * 3600
