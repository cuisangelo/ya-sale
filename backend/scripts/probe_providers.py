"""Check that the search and extraction credits answer Peru transport queries."""

import asyncio
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

# Executing this file puts scripts/ on sys.path, ahead of the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic

from app.connectors.base import SearchHit
from app.connectors.extractor import LegExtractor
from app.connectors.web_search import ExaConnector, TavilyConnector

# Client libraries log request targets; those lines can carry credentials.
logging.disable(logging.CRITICAL)

SOLES_PRICE = re.compile(r"S/\s?\d+")
MAX_RESULTS = 5


@dataclass(frozen=True)
class Trip:
    origin: str
    destination: str
    query: str


TRIPS = (
    Trip("Tarapoto", "Sauce", "colectivo Tarapoto a Sauce precio paradero"),
    Trip("Cusco", "Aguas Calientes", "como llegar de Cusco a Aguas Calientes tren combi precio"),
    Trip("Iquitos", "Nauta", "colectivo Iquitos a Nauta precio"),
)


@dataclass
class ProbeRow:
    provider: str
    configured: bool
    responds: bool
    useful: bool
    errored: bool


def _configured(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def _peru_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return host.endswith(".pe") or "peru" in host


def _ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def _flag(value: bool) -> str:
    return "yes" if value else "no"


def _print_summary(rows: list[ProbeRow]) -> None:
    print(f"{'provider':<12} {'configured':<12} {'responds':<10} useful")
    for row in rows:
        print(
            f"{row.provider:<12} {_flag(row.configured):<12} {_flag(row.responds):<10} {_flag(row.useful)}"
        )


async def _probe_search(provider: str, search, trips: tuple[Trip, ...]) -> tuple[list[SearchHit] | None, ProbeRow]:
    row = ProbeRow(provider, configured=True, responds=False, useful=False, errored=False)
    first_hits: list[SearchHit] | None = None
    for index, trip in enumerate(trips):
        started = time.perf_counter()
        try:
            hits = await search(trip.query, MAX_RESULTS)
        except Exception as exc:
            row.errored = True
            print(
                f"{provider} {trip.origin} -> {trip.destination} ERROR {type(exc).__name__} "
                f"{_ms(started)}ms hits=0 pe=0 soles=0"
            )
            continue
        pe = sum(1 for hit in hits if _peru_host(hit.url))
        soles = sum(1 for hit in hits if SOLES_PRICE.search(hit.content))
        row.responds = True
        if soles:
            row.useful = True
        if index == 0:
            first_hits = hits
        print(
            f"{provider} {trip.origin} -> {trip.destination} OK {_ms(started)}ms "
            f"hits={len(hits)} pe={pe} soles={soles}"
        )
    return first_hits, row


async def _probe_extractor(origin: str, destination: str, pages: list[SearchHit]) -> ProbeRow:
    row = ProbeRow("anthropic", configured=True, responds=False, useful=False, errored=False)
    started = time.perf_counter()
    try:
        legs = await LegExtractor(anthropic.AsyncAnthropic()).extract_legs(origin, destination, pages)
    except Exception as exc:
        row.errored = True
        print(
            f"anthropic {origin} -> {destination} ERROR {type(exc).__name__} "
            f"{_ms(started)}ms legs=0 priced=0"
        )
        return row
    priced = sum(
        1
        for leg in legs
        if leg.data.price_min_pen is not None or leg.data.price_max_pen is not None
    )
    row.responds = True
    row.useful = priced > 0
    print(f"anthropic {origin} -> {destination} OK {_ms(started)}ms legs={len(legs)} priced={priced}")
    return row


async def _run() -> int:
    rows: list[ProbeRow] = []
    first_hits: dict[str, list[SearchHit] | None] = {}

    tavily_key = _configured("TAVILY_API_KEY")
    exa_key = _configured("EXA_API_KEY")
    anthropic_key = _configured("ANTHROPIC_API_KEY") or _configured("ANTHROPIC_AUTH_TOKEN")

    if tavily_key:
        hits, row = await _probe_search("tavily", TavilyConnector(os.environ["TAVILY_API_KEY"]).search, TRIPS)
        first_hits["tavily"] = hits
        rows.append(row)
    else:
        print("tavily NOT CONFIGURED")
        rows.append(ProbeRow("tavily", configured=False, responds=False, useful=False, errored=False))

    if exa_key:
        hits, row = await _probe_search("exa", ExaConnector(os.environ["EXA_API_KEY"]).search, TRIPS)
        first_hits["exa"] = hits
        rows.append(row)
    else:
        print("exa NOT CONFIGURED")
        rows.append(ProbeRow("exa", configured=False, responds=False, useful=False, errored=False))

    if anthropic_key:
        pages = first_hits.get("tavily") or first_hits.get("exa") or []
        rows.append(await _probe_extractor(TRIPS[0].origin, TRIPS[0].destination, pages))
    else:
        print("anthropic NOT CONFIGURED")
        rows.append(ProbeRow("anthropic", configured=False, responds=False, useful=False, errored=False))

    print()
    _print_summary(rows)
    return 1 if any(row.errored for row in rows) else 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
