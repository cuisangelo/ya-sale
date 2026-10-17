import logging

import httpx
import pytest

from app.connectors.geocoding import GoogleGeocoder
from app.main import create_app
from app.places.domain import GeocodingFailed, Point

KEY = "secret-key"


def geocoder(handler) -> GoogleGeocoder:
    return GoogleGeocoder(KEY, httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def answer(body, status=200):
    return lambda request: httpx.Response(status, json=body)


def result(partial=False):
    found = {"geometry": {"location": {"lat": -6.48, "lng": -76.37}}, "formatted_address": "Tarapoto, Perú"}
    return found | ({"partial_match": True} if partial else {})


async def test_exact_match_is_a_point_and_the_search_stays_in_peru():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"status": "OK", "results": [result()]})

    assert await geocoder(handler).geocode("Tarapoto") == Point(-6.48, -76.37)
    assert seen[0].url.params["address"] == "Tarapoto"
    assert seen[0].url.params["components"] == "country:PE"


async def test_no_results_is_none():
    assert await geocoder(answer({"status": "ZERO_RESULTS", "results": []})).geocode("Xyzabc") is None


async def test_partial_match_is_another_place_so_it_is_none():
    assert await geocoder(answer({"status": "OK", "results": [result(partial=True)]})).geocode("Paradero X") is None


async def test_provider_errors_fail_loud_without_leaking_the_key():
    with pytest.raises(GeocodingFailed) as denied:
        await geocoder(answer({"status": "REQUEST_DENIED", "results": []})).geocode("Tarapoto")
    with pytest.raises(GeocodingFailed) as down:
        await geocoder(answer({}, status=503)).geocode("Tarapoto")

    def unreachable(request):
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(GeocodingFailed) as offline:
        await geocoder(unreachable).geocode("Tarapoto")
    for failure in (denied, down, offline):
        assert KEY not in str(failure.value)
        # The httpx exception quotes the URL with the key, so it must not ride along as context.
        assert failure.value.__cause__ is None
        assert failure.value.__context__ is None or failure.value.__suppress_context__


async def test_the_key_in_the_request_url_never_reaches_the_logs(settings, caplog):
    create_app(settings)
    caplog.set_level(logging.INFO)
    await geocoder(answer({"status": "OK", "results": [result()]})).geocode("Tarapoto")
    assert KEY not in caplog.text
