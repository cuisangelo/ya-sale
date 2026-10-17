"""Plan the demo routes through the real planner so stored legs exist before the demo."""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Executing this file puts scripts/ on sys.path, ahead of the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_settings
from app.db import bootstrap_schema, create_pool
from app.main import build_services
from app.trips.events import LegRefreshed, NoRoute, TripEvent, TripStarted
from app.trips.planner import TripPlanner

ROUTES = (
    ("Lima", "Sauce"),
    ("Cusco", "Aguas Calientes"),
    ("Iquitos", "Nauta"),
    ("Arequipa", "Chivay"),
    ("Lima", "Huaraz"),
    ("Puno", "Islas de los Uros"),
    ("Lima", "Paracas"),
    ("Tarapoto", "Lamas"),
)


@dataclass(frozen=True)
class RouteSummary:
    origin: str
    destination: str
    legs: int
    refreshed: int
    priced: int
    no_route: bool


def summarize(origin: str, destination: str, events: list[TripEvent]) -> RouteSummary:
    started = next((event for event in events if isinstance(event, TripStarted)), None)
    legs = started.legs_planned if started is not None else 0
    refreshed_events = [event for event in events if isinstance(event, LegRefreshed)]
    priced = sum(
        1
        for event in refreshed_events
        if event.version.data.price_min_pen is not None or event.version.data.price_max_pen is not None
    )
    return RouteSummary(
        origin=origin,
        destination=destination,
        legs=legs,
        refreshed=len(refreshed_events),
        priced=priced,
        no_route=any(isinstance(event, NoRoute) for event in events),
    )


async def _warm(planner: TripPlanner, origin: str, destination: str, trip_date: str) -> RouteSummary:
    # trip_id 0 because warm-up runs are not recorded as usage, so they never count as traction evidence.
    events = [event async for event in planner.plan(origin, destination, trip_date, trip_id=0)]
    return summarize(origin, destination, events)


async def _run() -> int:
    settings = load_settings(os.environ)
    pool = create_pool(settings.database_url)
    await pool.open()
    try:
        await bootstrap_schema(pool)
        services = build_services(settings, pool)
        today = date.today().isoformat()
        summaries = await asyncio.gather(
            *(_warm(services.planner, origin, destination, today) for origin, destination in ROUTES)
        )
    finally:
        await pool.close()

    total_legs = total_refreshed = total_priced = 0
    for summary in summaries:
        if summary.no_route:
            print(f"{summary.origin} -> {summary.destination}: NO ROUTE")
        else:
            print(
                f"{summary.origin} -> {summary.destination}: "
                f"legs={summary.legs} refreshed={summary.refreshed} priced={summary.priced}"
            )
        total_legs += summary.legs
        total_refreshed += summary.refreshed
        total_priced += summary.priced
    print(f"total: legs={total_legs} refreshed={total_refreshed} priced={total_priced}")
    return 1 if any(summary.no_route for summary in summaries) else 0


def main() -> None:
    # Client libraries log request targets; those lines can carry credentials.
    logging.disable(logging.CRITICAL)
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
