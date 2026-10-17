from datetime import UTC, datetime
from decimal import Decimal

from app.legs.domain import LegData, LegVersion
from app.trips.events import LegError, LegRefreshed, LegStored, NoRoute, TripStarted
from scripts.warm_routes import summarize

T0 = datetime(2026, 10, 17, tzinfo=UTC)


def version(price=None) -> LegVersion:
    return LegVersion(
        id=1,
        data=LegData(
            departure_point=None,
            operator=None,
            price_min_pen=Decimal(price[0]) if price else None,
            price_max_pen=Decimal(price[1]) if price else None,
            duration_min=None,
            schedule_note=None,
            purchase_url=None,
        ),
        source_url="https://example.pe",
        fetched_at=T0,
        confirmations=0,
    )


def test_counts_refreshed_prices_and_ignores_stored():
    events = [
        TripStarted(trip_id=0, origin="Lima", destination="Sauce", legs_planned=3, hops=()),
        LegRefreshed(0, 1, "bus", "Lima", "Sauce", "extracted", version(price=(10, 15)), ()),
        LegRefreshed(1, 2, "combi", "Lima", "Sauce", "extracted", version(), ()),
        LegStored(2, 3, "bus", "Lima", "Sauce", "extracted", version(price=(40, 50)), ()),
        LegError(index=3, mode="bus", message="timeout"),
    ]
    summary = summarize("Lima", "Sauce", events)
    assert (summary.legs, summary.refreshed, summary.priced, summary.no_route) == (3, 2, 1, False)


def test_no_route_only_has_zero_legs():
    summary = summarize("Cusco", "Aguas Calientes", [NoRoute(message="none")])
    assert summary.legs == 0
    assert summary.no_route is True
