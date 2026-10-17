export type LatLng = [number, number];

const ROUTER = "https://router.project-osrm.org/route/v1/driving";
const cache = new Map<string, Promise<LatLng[]>>();

// Tab switches and re-renders ask for the same pair again; one request per pair is enough.
export function roadPath(from: LatLng, to: LatLng, fetcher: typeof fetch = fetch): Promise<LatLng[]> {
  const key = `${from.join(",")};${to.join(",")}`;
  let path = cache.get(key);
  if (!path) {
    path = fetchRoad(from, to, fetcher);
    cache.set(key, path);
    path.catch(() => cache.delete(key));
  }
  return path;
}

async function fetchRoad(from: LatLng, to: LatLng, fetcher: typeof fetch): Promise<LatLng[]> {
  const url = `${ROUTER}/${from[1]},${from[0]};${to[1]},${to[0]}?overview=simplified&geometries=geojson`;
  const response = await fetcher(url);
  if (!response.ok) throw new Error(`Road router HTTP ${response.status}`);
  return parseRoad(await response.json(), from, to);
}

export function parseRoad(body: unknown, from: LatLng, to: LatLng): LatLng[] {
  const route = body as { code?: string; routes?: { geometry?: { coordinates?: [number, number][] } }[] };
  const coordinates = route.routes?.[0]?.geometry?.coordinates;
  if (route.code !== "Ok" || !coordinates || coordinates.length < 2) {
    throw new Error(`Road router returned no route: ${route.code ?? "unknown"}`);
  }
  // The router snaps both ends to the nearest road; the markers sit on the places themselves.
  return [from, ...coordinates.map(([lng, lat]): LatLng => [lat, lng]), to];
}
