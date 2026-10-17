import httpx

from app.places.domain import GeocodingFailed, Point

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class GoogleGeocoder:
    """Google's Geocoding API, restricted to Peru. A partial match is a different place, so it counts as none."""

    def __init__(self, api_key: str, client: httpx.AsyncClient):
        self._api_key = api_key
        self._client = client

    async def geocode(self, place: str) -> Point | None:
        params = {"address": place, "components": "country:PE", "language": "es", "key": self._api_key}
        # The API only takes the key in the query string, so no httpx error text (it quotes the URL) leaves here.
        try:
            response = await self._client.get(GEOCODE_URL, params=params)
        except httpx.HTTPError as exc:
            raise GeocodingFailed(type(exc).__name__) from None
        if response.status_code != 200:
            raise GeocodingFailed(f"HTTP {response.status_code}")
        body = response.json()
        if body["status"] == "ZERO_RESULTS":
            return None
        if body["status"] != "OK":
            raise GeocodingFailed(body["status"])
        best = body["results"][0]
        if best.get("partial_match"):
            return None
        location = best["geometry"]["location"]
        return Point(location["lat"], location["lng"])
