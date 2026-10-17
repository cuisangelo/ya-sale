import { expect, test, vi } from "vitest";
import { parseRoad, roadPath, type LatLng } from "./roads";

const LIMA: LatLng = [-12.05, -77.04];
const TARAPOTO: LatLng = [-6.49, -76.36];

function routed(coordinates: [number, number][]) {
  return { code: "Ok", routes: [{ geometry: { coordinates } }] };
}

test("flips the router's lng,lat pairs and pins both ends to the places", () => {
  const path = parseRoad(
    routed([
      [-77.03, -12.04],
      [-76.9, -9.3],
      [-76.37, -6.5],
    ]),
    LIMA,
    TARAPOTO,
  );
  expect(path).toEqual([LIMA, [-12.04, -77.03], [-9.3, -76.9], [-6.5, -76.37], TARAPOTO]);
});

test("rejects an answer without a route", () => {
  expect(() => parseRoad({ code: "NoRoute", routes: [] }, LIMA, TARAPOTO)).toThrow("NoRoute");
});

test("asks the router once per pair and again after a failure", async () => {
  const ok = new Response(JSON.stringify(routed([[-77.03, -12.04], [-76.37, -6.5]])));
  const fetcher = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(new Response("busy", { status: 503 }))
    .mockResolvedValueOnce(ok);

  await expect(roadPath(LIMA, TARAPOTO, fetcher)).rejects.toThrow("503");
  const first = await roadPath(LIMA, TARAPOTO, fetcher);
  const second = await roadPath(LIMA, TARAPOTO, fetcher);

  expect(second).toBe(first);
  expect(fetcher).toHaveBeenCalledTimes(2);
});
