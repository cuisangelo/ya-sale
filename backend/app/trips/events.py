from dataclasses import dataclass

from app.departures.domain import Departure
from app.legs.domain import LegOption, LegStatus, LegVersion, Mode
from app.places.domain import MapPoint
from app.trips.domain import PlannedHop


@dataclass(frozen=True)
class TripStarted:
    trip_id: int
    origin: str
    destination: str
    legs_planned: int
    hops: tuple[PlannedHop, ...]


@dataclass(frozen=True)
class LegStored:
    index: int
    leg_id: int
    mode: Mode
    origin: str
    destination: str
    status: LegStatus
    version: LegVersion
    options: tuple[LegOption, ...]


@dataclass(frozen=True)
class LegRefreshed:
    index: int
    leg_id: int
    mode: Mode
    origin: str
    destination: str
    status: LegStatus
    version: LegVersion
    options: tuple[LegOption, ...]


@dataclass(frozen=True)
class LegError:
    index: int
    mode: Mode
    message: str


@dataclass(frozen=True)
class LegDepartures:
    index: int
    mode: Mode
    departures: tuple[Departure, ...]


@dataclass(frozen=True)
class TripMapped:
    points: tuple[MapPoint, ...]


@dataclass(frozen=True)
class NoRoute:
    message: str


@dataclass(frozen=True)
class TripDone:
    legs: int


TripEvent = TripStarted | LegStored | LegRefreshed | LegError | LegDepartures | TripMapped | NoRoute | TripDone
