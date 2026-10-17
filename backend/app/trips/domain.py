from collections.abc import Iterable
from dataclasses import dataclass

from app.legs.domain import Mode

# One alternative is enough to compare (bus or plane); more would spend the search budget on noise.
MAX_MODES_PER_HOP = 2


@dataclass(frozen=True)
class PlannedHop:
    origin: str
    destination: str
    modes: tuple[Mode, ...]  # the way the pages describe first, then the alternatives they also name

    @classmethod
    def of(cls, origin: str, destination: str, mode: Mode, alternatives: Iterable[Mode]) -> "PlannedHop":
        modes = tuple(dict.fromkeys([mode, *alternatives]))
        return cls(origin, destination, modes[:MAX_MODES_PER_HOP])
