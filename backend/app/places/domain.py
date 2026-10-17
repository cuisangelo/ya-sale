from dataclasses import dataclass


class GeocodingFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class Point:
    lat: float
    lng: float


@dataclass(frozen=True)
class MapPoint:
    name: str
    lat: float
    lng: float
