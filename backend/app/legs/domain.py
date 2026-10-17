import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

Mode = Literal[
    "bus", "avion", "tren", "colectivo", "combi", "custer", "bus_urbano",
    "metro", "mototaxi", "moto", "lancha", "bote", "balsa",
]
LegStatus = Literal["extracted", "confirmed", "disputed"]

# Live sources rarely repeat the exact same minutes; smaller swings are the same trip.
DURATION_TOLERANCE = 0.25


def normalize_place(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents).strip().lower()


@dataclass(frozen=True)
class LegKey:
    origin: str
    destination: str
    mode: Mode

    @classmethod
    def of(cls, origin: str, destination: str, mode: Mode) -> "LegKey":
        return cls(normalize_place(origin), normalize_place(destination), mode)


@dataclass(frozen=True)
class LegData:
    departure_point: str | None
    operator: str | None
    price_min_pen: Decimal | None
    price_max_pen: Decimal | None
    duration_min: int | None
    schedule_note: str | None
    purchase_url: str | None


@dataclass(frozen=True)
class LegVersion:
    id: int
    data: LegData
    source_url: str
    fetched_at: datetime
    confirmations: int


def _price_change(a: LegData, b: LegData) -> bool:
    if None in (a.price_min_pen, a.price_max_pen, b.price_min_pen, b.price_max_pen):
        return False
    return a.price_max_pen < b.price_min_pen or b.price_max_pen < a.price_min_pen


def _duration_change(a: LegData, b: LegData) -> bool:
    if a.duration_min is None or b.duration_min is None:
        return False
    return abs(a.duration_min - b.duration_min) > DURATION_TOLERANCE * a.duration_min


def _departure_change(a: LegData, b: LegData) -> bool:
    if a.departure_point is None or b.departure_point is None:
        return False
    return normalize_place(a.departure_point) != normalize_place(b.departure_point)


def material_change(a: LegData, b: LegData) -> bool:
    return _price_change(a, b) or _duration_change(a, b) or _departure_change(a, b)


def display_version(versions: list[LegVersion]) -> LegVersion:
    if leg_status(versions) == "confirmed":
        return next(v for v in reversed(versions) if v.confirmations > 0)
    return versions[-1]


def leg_status(versions: list[LegVersion]) -> LegStatus:
    confirmed_indexes = [i for i, v in enumerate(versions) if v.confirmations > 0]
    if not confirmed_indexes:
        return "extracted"
    newest_confirmed = confirmed_indexes[-1]
    reference = versions[newest_confirmed].data
    if any(material_change(reference, later.data) for later in versions[newest_confirmed + 1:]):
        return "disputed"
    return "confirmed"
