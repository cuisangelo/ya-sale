import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Schedule(StrEnum):
    DAY = "day"
    NIGHT = "night"


@dataclass(frozen=True)
class TravelerPreferences:
    """What a traveler explicitly chose; route facts never come from here."""

    schedule: Schedule | None
    cheapest: bool


class PreferencesUnavailable(RuntimeError):
    """The preference store did not answer in time or answered something unusable."""


class PreferenceStore(Protocol):
    async def load(self, subject: str) -> TravelerPreferences | None: ...

    async def save(self, subject: str, preferences: TravelerPreferences) -> None: ...

    async def clear(self, subject: str) -> None: ...


_PREFIX = "Ya Sale traveler preferences:"
_TEXT = re.compile(rf"^{re.escape(_PREFIX)} departure time = (any|day|night); cheapest fare = (yes|no)\.$")


def memory_text(preferences: TravelerPreferences) -> str:
    """One self-describing sentence, so the stored memory reads correctly in any memory console."""
    schedule = preferences.schedule.value if preferences.schedule else "any"
    cheapest = "yes" if preferences.cheapest else "no"
    return f"{_PREFIX} departure time = {schedule}; cheapest fare = {cheapest}."


def parse_memory_text(text: str) -> TravelerPreferences | None:
    """Reads back only what memory_text wrote; anything else in the subject is ignored."""
    match = _TEXT.match(text.strip())
    if not match:
        return None
    schedule, cheapest = match.groups()
    return TravelerPreferences(None if schedule == "any" else Schedule(schedule), cheapest == "yes")
