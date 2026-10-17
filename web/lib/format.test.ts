import { expect, test } from "vitest";
import { initialTripState, reduceTrip, type Departure, type LegSlot, type Mode, type Option, type TripState, type Version } from "./api";
import {
  datedLink,
  departureClock,
  departuresHeading,
  firstDeparture,
  initials,
  itineraryTotals,
  logoDomain,
  logoSrc,
  mapsDirectionsUrl,
  optionLink,
  priceFloor,
  seatsLabel,
  tripDayLabel,
} from "./format";

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

test("departure times read as the Lima clock whatever the viewer's zone", () => {
  expect(departureClock("2026-10-25T19:30:00-05:00")).toBe("19:30");
  expect(departureClock("2026-10-26T00:05:00Z")).toBe("19:05");
});

test("the departures heading names the trip day", () => {
  expect(departuresHeading("2026-10-25")).toBe("Salidas del domingo 25 de octubre");
});

test("the trip pill names the day in short form", () => {
  expect(tripDayLabel("2026-10-20")).toBe("mar 20 oct");
});

test("seats read in singular and plural, and unknown seats say nothing", () => {
  expect(seatsLabel(1)).toBe("1 asiento libre");
  expect(seatsLabel(12)).toBe("12 asientos libres");
  expect(seatsLabel(0)).toBe("agotado");
  expect(seatsLabel(null)).toBeNull();
});

test("links to sellers that take the trip in the URL open that day's search", () => {
  const trip = { origin: "Lima", destination: "Huancayo", date: "2026-10-25" };
  expect(datedLink("https://kupos.pe/es/pasajes-bus/lima,peru/huancayo,peru?date_onward=17-10-2026", trip)).toBe(
    "https://kupos.pe/es/pasajes-bus/lima,peru/huancayo,peru?date_onward=25-10-2026",
  );
  expect(datedLink("https://www.civa.com.pe/", { ...trip, destination: "Cerro de Pasco" })).toBe(
    "https://www.civa.com.pe/es/pasajes-bus/lima,peru/cerro-de-pasco,peru?date_onward=25-10-2026",
  );
  expect(datedLink("https://www.skyairline.com/peru", { ...trip, destination: "Cusco" })).toBe(
    "https://initial-sale.skyairline.com/es/peru?origin=LIM&destination=CUZ&departureDate=2026-10-25&arrivalDate=2026-10-25&flightType=OW&ADT=1",
  );
});

test("links that cannot carry the trip stay as they are", () => {
  const trip = { origin: "Lima", destination: "Sauce", date: "2026-10-25" };
  expect(datedLink("https://www.skyairline.com/peru", trip)).toBe("https://www.skyairline.com/peru");
  expect(datedLink("https://www.movilbus.pe/", trip)).toBe("https://www.movilbus.pe/");
  expect(datedLink(null, trip)).toBeNull();
});

function departure(operator: string, departs_at: string): Departure {
  return {
    operator,
    departs_at,
    arrives_at: null,
    price_pen: "143",
    seats_available: null,
    booking_url: "https://example.test",
    seller: "example",
  };
}

function withDepartures(index: number, mode: Mode, departures: Departure[]): TripState {
  return reduceTrip(initialTripState, { event: "leg_departures", data: { index, mode, departures } });
}

test("firstDeparture picks the earliest of hop 0", () => {
  const state = withDepartures(0, "bus", [
    departure("Cruz del Sur", "2026-10-20T21:00:00-05:00"),
    departure("Civa", "2026-10-20T12:00:00-05:00"),
  ]);
  expect(firstDeparture(state, "bus")).toEqual({ time: "12:00", operator: "Civa" });
});

test("firstDeparture reads a midnight bus as 00:xx, never 24:xx", () => {
  const state = withDepartures(0, "bus", [departure("Civa", "2026-10-21T00:05:00-05:00")]);
  expect(firstDeparture(state, "bus")).toEqual({ time: "00:05", operator: "Civa" });
});

test("firstDeparture ignores later hops", () => {
  const state = withDepartures(1, "bus", [departure("Civa", "2026-10-20T06:00:00-05:00")]);
  expect(firstDeparture(state, "bus")).toBeNull();
});

test("firstDeparture returns null for an unknown mode", () => {
  const state = withDepartures(0, "bus", [departure("Civa", "2026-10-20T12:00:00-05:00")]);
  expect(firstDeparture(state, "avion")).toBeNull();
  expect(firstDeparture(state, undefined)).toBeNull();
});
