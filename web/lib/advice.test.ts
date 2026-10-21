import { afterEach, expect, test, vi } from "vitest";
import { preferenceLabels, routeAdvice } from "./advice";
import {
  clearPreferences,
  initialTripState,
  parsePreferencesState,
  reduceTrip,
  savePreferences,
  type Departure,
  type Mode,
  type TripState,
} from "./api";

function departure(time: string, operator: string, price: string | null, seats: number | null = 10): Departure {
  return {
    operator,
    departs_at: `2026-10-22T${time}:00-05:00`,
    arrives_at: null,
    price_pen: price,
    seats_available: seats,
    booking_url: `https://${operator.toLowerCase().replace(/ /g, "")}.pe/${time}`,
    seller: "seller.pe",
  };
}

function trip(departures: Departure[], modes: Mode[] = ["bus"]): TripState {
  const started = reduceTrip(initialTripState, {
    event: "trip_started",
    data: { trip_id: 1, origin: "Lima", destination: "Trujillo", legs_planned: 1, hops: [{ origin: "Lima", destination: "Trujillo", modes }] },
  });
  return reduceTrip(started, { event: "leg_departures", data: { index: 0, mode: modes[0], departures } });
}

const DEPARTURES = [
  departure("08:30", "Oltursa", "70"),
  departure("21:00", "Cruz del Sur", "95"),
  departure("22:30", "Linea", "60"),
  departure("23:59", "Ittsa", "40", 0),
];

test("night travelers get the first night departure that still has seats", () => {
  const advice = routeAdvice(trip(DEPARTURES), ["bus"], { schedule: "night", cheapest: false });
  expect(advice).toEqual([
    { hop: "Lima → Trujillo", title: "Primera salida de noche", detail: "21:00 · Cruz del Sur · S/95", link: "https://cruzdelsur.pe/21:00" },
  ]);
});

test("cheapest skips sold-out departures", () => {
  const advice = routeAdvice(trip(DEPARTURES), ["bus"], { schedule: null, cheapest: true });
  expect(advice.map((item) => item.detail)).toEqual(["22:30 · Linea · S/60"]);
});

test("says plainly when no departure fits the saved schedule", () => {
  const advice = routeAdvice(trip([departure("08:30", "Oltursa", "70")]), ["bus"], { schedule: "night", cheapest: false });
  expect(advice).toEqual([
    { hop: "Lima → Trujillo", title: "Ninguna salida de noche", detail: "Revisamos la salida publicada para tu fecha.", link: null },
  ]);
});

test("without departures nothing is invented", () => {
  expect(routeAdvice(trip([]), ["bus"], { schedule: "day", cheapest: true })).toEqual([]);
});

test("without departures, cheapest compares the dated fares of each mode", () => {
  const leg = (mode: Mode, legId: number, price: string) => ({
    index: 0,
    leg_id: legId,
    mode,
    origin: "Cusco",
    destination: "Ollantaytambo",
    status: "extracted" as const,
    options: [],
    version: {
      id: legId,
      departure_point: null,
      operator: null,
      price_min_pen: price,
      price_max_pen: null,
      duration_min: 90,
      schedule_note: null,
      purchase_url: null,
      source_url: "https://fuente.pe/x",
      fetched_at: "2026-10-17T15:00:00Z",
      confirmations: 0,
    },
  });
  let state = trip([], ["combi", "tren"]);
  state = reduceTrip(state, { event: "leg_stored", data: leg("combi", 1, "10") });
  state = reduceTrip(state, { event: "leg_stored", data: leg("tren", 2, "120") });
  const advice = routeAdvice(state, ["tren"], { schedule: null, cheapest: true });
  expect(advice).toHaveLength(1);
  expect(advice[0].title).toBe("Más barato en combi");
  expect(advice[0].detail).toMatch(/^S\/10 · según fuente\.pe · 17 oct/);
});

test("labels name each saved choice", () => {
  expect(preferenceLabels({ schedule: "day", cheapest: true })).toEqual(["Salir de día", "Precio más bajo"]);
});

test("parsePreferencesState reads enabled, saved and empty answers", () => {
  expect(parsePreferencesState({ enabled: false, preferences: null })).toEqual({ enabled: false, preferences: null });
  expect(parsePreferencesState({ enabled: true, preferences: { schedule: "night", cheapest: false } })).toEqual({
    enabled: true,
    preferences: { schedule: "night", cheapest: false },
  });
  expect(() => parsePreferencesState({ enabled: true, preferences: { schedule: "noon", cheapest: false } })).toThrow();
});

afterEach(() => vi.unstubAllGlobals());

test("saving sends consent with the choice, and clearing sends DELETE", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal("fetch", async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({ enabled: true, preferences: null }), { status: 200 });
  });
  await savePreferences({ schedule: "night", cheapest: true });
  await clearPreferences();
  expect(calls[0].init.method).toBe("PUT");
  expect(JSON.parse(String(calls[0].init.body))).toEqual({ schedule: "night", cheapest: true, consent: true });
  expect(calls[1]).toMatchObject({ url: "/api/travelers/me/preferences", init: { method: "DELETE", body: undefined } });
});

test("a provider failure surfaces the server's message", async () => {
  vi.stubGlobal("fetch", async () =>
    new Response(JSON.stringify({ detail: "No se guardaron tus preferencias: el servicio de memoria no respondió." }), { status: 503 }),
  );
  await expect(savePreferences({ schedule: "day", cheapest: false })).rejects.toThrow("No se guardaron tus preferencias");
});
