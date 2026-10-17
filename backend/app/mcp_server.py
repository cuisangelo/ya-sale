from collections.abc import Callable

from mcp.server.mcpserver import MCPServer

from app.departures.serialization import departure_json
from app.legs.domain import display_version, leg_status
from app.legs.repository import AlreadyConfirmed
from app.legs.serialization import leg_summary_json, version_json
from app.trips.events import LegDepartures, LegError, LegRefreshed, LegStored, NoRoute

CONFIRMATION_FINGERPRINT = "mcp"


def build_mcp(services: Callable[[], object]) -> MCPServer:
    server = MCPServer(
        name="Ya Sale",
        instructions=(
            "Arma viajes en el Perú de cualquier origen a cualquier destino, tramo por tramo y en cualquier "
            "medio de transporte, con la fuente y la fecha de cada dato."
        ),
    )

    @server.tool()
    async def plan_trip(origin: str, destination: str, date: str) -> dict:
        """Plan a trip in Peru leg by leg (bus, plane, train, colectivo, combi, mototaxi, boat), with sources.

        `date` is YYYY-MM-DD. For every leg mode a live seller covers, it also returns the departures on sale
        that day, each with its time, price and free seats when known, and a booking_url that opens it.
        """
        latest: dict[tuple[int, str], dict] = {}
        departures: list[dict] = []
        notes: list[str] = []
        async for event in services().planner.plan(origin, destination, date, trip_id=0):
            if isinstance(event, (LegStored, LegRefreshed)):
                latest[(event.index, event.mode)] = leg_summary_json(event.leg_id, event.mode, event.origin, event.destination, event.status, event.version)
            elif isinstance(event, LegDepartures):
                departures.append({"index": event.index, "mode": event.mode, "departures": [departure_json(d) for d in event.departures]})
            elif isinstance(event, (LegError, NoRoute)):
                notes.append(event.message)
        return {"legs": [latest[i] for i in sorted(latest)], "departures": departures, "notes": notes}

    @server.tool()
    async def get_leg(leg_id: int) -> dict:
        """Get one leg with every saved version and its trust status."""
        key, versions = await services().legs.get(leg_id)
        return {
            **leg_summary_json(leg_id, key.mode, key.origin, key.destination, leg_status(versions), display_version(versions)),
            "versions": [version_json(v) for v in versions],
        }

    @server.tool()
    async def confirm_leg(leg_id: int, version_id: int, display_name: str | None = None) -> dict:
        """Confirm a leg version you have travelled yourself."""
        legs = services().legs
        try:
            await legs.confirm(version_id, CONFIRMATION_FINGERPRINT, display_name)
        except AlreadyConfirmed:
            return {"error": "Ya se confirmó este tramo desde el MCP."}
        key, versions = await legs.get(leg_id)
        return leg_summary_json(leg_id, key.mode, key.origin, key.destination, leg_status(versions), display_version(versions))

    return server
