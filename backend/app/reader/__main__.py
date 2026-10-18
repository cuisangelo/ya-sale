import argparse
import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import date

import anthropic

from app.db import bootstrap_schema, create_pool
from app.reader import worker
from app.reader.browser import chromium
from app.reader.discovery import Discoverer
from app.reader.domain import Query
from app.reader.extraction import DepartureExtractor
from app.reader.registry import BY_DOMAIN
from app.reader.repository import RecipeRepository, RequestQueue, ResultRepository
from app.reader.service import ReaderService


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


@asynccontextmanager
async def _reader():
    """The composition root: one browser, one database pool and one Claude client, wired into the service."""
    client = anthropic.AsyncAnthropic(api_key=_required("ANTHROPIC_API_KEY"))
    pool = create_pool(_required("DATABASE_URL"))
    await pool.open()
    await bootstrap_schema(pool)
    try:
        async with chromium(headless=False) as browser:
            service = ReaderService(
                RecipeRepository(pool), ResultRepository(pool), Discoverer(client), DepartureExtractor(client), browser.tab
            )
            yield service, RequestQueue(pool)
    finally:
        await pool.close()


async def _read(args) -> None:
    site = BY_DOMAIN[args.domain]
    query = Query(args.origin, args.destination, date.fromisoformat(args.date))
    async with _reader() as (service, _):
        started = time.monotonic()
        found = await service.read(site, query)
    print(f"status={found.status} discovered={found.discovered} seconds={time.monotonic() - started:.1f} "
          f"model_calls={found.usage.calls} cost_usd={found.usage.cost_usd}")
    for d in found.departures:
        print(f"  {d.departs_at:%H:%M} {d.operator} S/{d.price_pen} seats={d.seats_available} {d.booking_url}")


async def _worker(_args) -> None:
    async with _reader() as (service, queue):
        await worker.run(queue, service, BY_DOMAIN)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # The HTTP clients log every request at INFO, which buries the reader's own lines.
    for noisy in ("httpx", "httpx2"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog="python -m app.reader")
    commands = parser.add_subparsers(dest="command", required=True)
    read = commands.add_parser("read", help="read one operator's departures now and store them")
    read.add_argument("domain", choices=sorted(BY_DOMAIN))
    read.add_argument("origin")
    read.add_argument("destination")
    read.add_argument("date", help="YYYY-MM-DD")
    commands.add_parser("worker", help="drain the reader_requests queue forever")
    args = parser.parse_args()
    asyncio.run({"read": _read, "worker": _worker}[args.command](args))


main()
