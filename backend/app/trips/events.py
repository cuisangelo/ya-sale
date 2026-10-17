from dataclasses import dataclass

from app.legs.domain import LegStatus, LegVersion, Mode


@dataclass(frozen=True)
class TripStarted:
    trip_id: int
    origin: str
    destination: str
    legs_planned: int


@dataclass(frozen=True)
class LegStored:
    index: int
    leg_id: int
    mode: Mode
    origin: str
    destination: str
    status: LegStatus
    version: LegVersion


@dataclass(frozen=True)
class LegRefreshed:
    index: int
    leg_id: int
    mode: Mode
    origin: str
    destination: str
    status: LegStatus
    version: LegVersion


@dataclass(frozen=True)
class LegError:
    index: int
    message: str


@dataclass(frozen=True)
class NoRoute:
    message: str


@dataclass(frozen=True)
class TripDone:
    legs: int


TripEvent = TripStarted | LegStored | LegRefreshed | LegError | NoRoute | TripDone
