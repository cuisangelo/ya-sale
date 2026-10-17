import { expect, test } from "vitest";
import type { LegSlot, Option, Version } from "./api";
import { itineraryTotals, mapsDirectionsUrl, priceFloor } from "./format";

function version(prices: [string | null, string | null], duration: number | null = 60): Version {
  return {
    id: 1,
    departure_point: null,
    operator: null,
    price_min_pen: prices[0],
    price_max_pen: prices[1],
    duration_min: duration,
    schedule_note: null,
    purchase_url: null,
    source_url: "https://example.test",
    fetched_at: "2026-10-17T12:00:00Z",
    confirmations: 0,
  };
}

function option(prices: [string | null, string | null]): Option {
  const { id, confirmations, ...rest } = version(prices);
  void id;
  void confirmations;
  return rest;
}

function slot(prices: [string | null, string | null], duration: number | null): LegSlot {
  return {
    index: 0,
    mode: "bus",
    options: [],
    live: true,
    error: null,
    summary: { leg_id: 1, mode: "bus", origin: "A", destination: "B", status: "extracted", version: version(prices, duration) },
  };
}

test("maps link asks for directions to the departure point in its town", () => {
  const url = new URL(mapsDirectionsUrl("Paradero de la Banda de Shilcayo", "Tarapoto"));
  expect(url.origin + url.pathname).toBe("https://www.google.com/maps/dir/");
  expect(url.searchParams.get("api")).toBe("1");
  expect(url.searchParams.get("destination")).toBe("Paradero de la Banda de Shilcayo, Tarapoto, Perú");
});

test("price floor is the cheapest price among the leg and its options", () => {
  expect(priceFloor(version(["143", "144"]), [option(["55", "55"]), option([null, null]), option(["190", null])])).toBe("desde S/55");
  expect(priceFloor(version([null, null]), [option([null, null])])).toBeNull();
});

test("totals add the selected legs and stay unknown when one leg has no price", () => {
  expect(itineraryTotals([slot(["100", "140"], 1560), slot(["15", "15"], 105)])).toEqual({
    price: "S/115–155",
    duration: "27 h 45 min",
  });
  expect(itineraryTotals([slot(["100", "140"], 1560), slot([null, null], null)])).toEqual({ price: null, duration: null });
});
