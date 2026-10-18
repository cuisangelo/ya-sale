from datetime import UTC, datetime, timedelta

from app.trips.domain import PlannedHop
from app.trips.repository import RouteRepository

CHAIN = [PlannedHop("Lima", "Tarapoto", ("bus", "avion")), PlannedHop("Tarapoto", "Sauce", ("colectivo",))]


async def test_a_stored_route_comes_back_with_its_hops_in_order(pool):
    routes = RouteRepository(pool)
    now = datetime.now(UTC)
    await routes.store("lima→sauce", CHAIN, now)
    assert await routes.cached("lima→sauce", now - timedelta(days=7)) == CHAIN


async def test_a_route_planned_before_the_cutoff_is_not_returned(pool):
    routes = RouteRepository(pool)
    now = datetime.now(UTC)
    await routes.store("lima→sauce", CHAIN, now - timedelta(days=8))
    assert await routes.cached("lima→sauce", now - timedelta(days=7)) is None


async def test_storing_again_replaces_the_route(pool):
    routes = RouteRepository(pool)
    now = datetime.now(UTC)
    await routes.store("lima→sauce", CHAIN, now)
    await routes.store("lima→sauce", CHAIN[:1], now)
    assert await routes.cached("lima→sauce", now - timedelta(days=7)) == CHAIN[:1]
