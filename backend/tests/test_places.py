import pytest

from app.places.domain import GeocodingFailed, Point
from app.places.locator import PlaceLocator
from app.places.repository import PlaceRepository


class FakeGeocoder:
    def __init__(self, places, failing=False):
        self._places = places
        self._failing = failing
        self.calls = []

    async def geocode(self, place):
        self.calls.append(place)
        if self._failing:
            raise GeocodingFailed("OVER_QUERY_LIMIT")
        return self._places.get(place)


@pytest.fixture
def repo(pool):
    return PlaceRepository(pool)


async def test_a_place_is_geocoded_once_then_read_from_the_cache(repo):
    geocoder = FakeGeocoder({"Tarapoto": Point(-6.48, -76.37)})
    locator = PlaceLocator(repo, geocoder)
    assert await locator.locate("Tarapoto") == Point(-6.48, -76.37)
    assert await locator.locate("  tarapoto ") == Point(-6.48, -76.37)
    assert geocoder.calls == ["Tarapoto"]


async def test_a_place_that_was_not_found_is_not_asked_again(repo):
    geocoder = FakeGeocoder({})
    locator = PlaceLocator(repo, geocoder)
    assert await locator.locate("Xyzabc") is None
    assert await locator.locate("Xyzabc") is None
    assert geocoder.calls == ["Xyzabc"]


async def test_a_failed_lookup_is_not_cached(repo):
    with pytest.raises(GeocodingFailed):
        await PlaceLocator(repo, FakeGeocoder({}, failing=True)).locate("Tarapoto")
    geocoder = FakeGeocoder({"Tarapoto": Point(-6.48, -76.37)})
    assert await PlaceLocator(repo, geocoder).locate("Tarapoto") == Point(-6.48, -76.37)
