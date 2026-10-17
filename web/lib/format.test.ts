import { expect, test } from "vitest";
import type { LegSlot, Option, Version } from "./api";
import { initials, itineraryTotals, logoDomain, logoSrc, mapsDirectionsUrl, optionLink, priceFloor } from "./format";

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

test("optionLink opens the purchase page, else the operator's own site, else the page it was read from", () => {
  const buscobus = "https://buscobus.pe/horarios-y-pasajes/lima-barranca-en-bus/";
  const link = (operator: string | null, purchase_url: string | null, source_url = buscobus) =>
    optionLink({ operator, purchase_url, source_url });
  expect(link("Movil Tours", "https://kupos.pe/es/pasajes-bus/lima,peru/barranca,peru")).toBe(
    "https://kupos.pe/es/pasajes-bus/lima,peru/barranca,peru",
  );
  expect(link("Movil Tours", null)).toBe("https://www.movilbus.pe/");
  expect(link("Perú Rail", null)).toBe("https://www.perurail.com/");
  expect(link("LATAM Airlines", null)).toBe("https://www.latamairlines.com/pe/es");
  expect(link("Línea 44", null)).toBe(buscobus);
  expect(link("Automovil Express", null)).toBe(buscobus);
  expect(link(null, "javascript:alert(1)", "ftp://x.test/a")).toBeNull();
});

test("logoDomain is the site the option's link opens", () => {
  expect(logoDomain("https://www.checkmybus.pe/lima-lp/tarapoto-sm")).toBe("checkmybus.pe");
  expect(logoDomain("https://www.movilbus.pe/")).toBe("movilbus.pe");
  expect(logoDomain(null)).toBeNull();
});

test("logoSrc points at the logo stored with the web", () => {
  expect(logoSrc("checkmybus.pe")).toBe("/logos/checkmybus.pe.png");
});

test("initials stand in for a missing logo", () => {
  expect(initials("Via Pacifico")).toBe("VP");
  expect(initials("TSP")).toBe("T");
  expect(initials("Turismo Amanecer Selva")).toBe("TA");
});
