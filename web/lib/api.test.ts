import { expect, test } from "vitest";
import { initialTripState, parseSse, reduceTrip, type LegSummary } from "./api";

function version(id: number) {
  return {
    id,
    departure_point: null,
    operator: null,
    price_min_pen: "12.50",
    price_max_pen: null,
    duration_min: 90,
    schedule_note: null,
    purchase_url: null,
    source_url: "https://example.test/source",
    fetched_at: "2026-10-17T12:00:00Z",
    confirmations: 0,
  };
}

function leg(overrides: Partial<LegSummary> = {}): LegSummary {
  return {
    leg_id: 1,
    mode: "bus",
    origin: "Cusco",
    destination: "Aguas Calientes",
    status: "extracted",
    version: version(7),
    ...overrides,
  };
}

test("refreshed replaces stored for the same index and marks it live", () => {
  const started = reduceTrip(initialTripState, {
    event: "trip_started",
    data: { trip_id: 4, origin: "Cusco", destination: "Aguas Calientes", legs_planned: 2 },
  });
  const stored = reduceTrip(started, {
    event: "leg_stored",
    data: { index: 0, ...leg({ leg_id: 10, destination: "Ollantaytambo" }) },
  });

  expect(stored.legs).toHaveLength(1);
  expect(stored.legs[0]).toMatchObject({
    index: 0,
    live: false,
    error: null,
    summary: { leg_id: 10, destination: "Ollantaytambo" },
  });

  const refreshed = reduceTrip(stored, {
    event: "leg_refreshed",
    data: {
      index: 0,
      ...leg({ leg_id: 10, destination: "Aguas Calientes", status: "confirmed", version: version(8) }),
    },
  });

  expect(refreshed.legs).toHaveLength(1);
  expect(refreshed.legs[0]).toMatchObject({
    index: 0,
    live: true,
    error: null,
    summary: { leg_id: 10, destination: "Aguas Calientes", status: "confirmed" },
  });
  expect(refreshed.legs[0].summary?.version.id).toBe(8);
});

test("leg_error keeps the stored leg and flags it", () => {
  let state = reduceTrip(initialTripState, {
    event: "trip_started",
    data: { trip_id: 1, origin: "Lima", destination: "Sauce", legs_planned: 2 },
  });
  state = reduceTrip(state, {
    event: "leg_stored",
    data: { index: 0, ...leg({ leg_id: 3, origin: "Lima", destination: "Tarapoto" }) },
  });
  state = reduceTrip(state, {
    event: "leg_refreshed",
    data: { index: 0, ...leg({ leg_id: 3, origin: "Lima", destination: "Tarapoto", version: version(9) }) },
  });
  state = reduceTrip(state, {
    event: "leg_error",
    data: { index: 0, message: "La fuente no respondió" },
  });

  expect(state.legs[0].summary).toMatchObject({ leg_id: 3, destination: "Tarapoto" });
  expect(state.legs[0].summary?.version.id).toBe(9);
  expect(state.legs[0].live).toBe(true);
  expect(state.legs[0].error).toBe("La fuente no respondió");

  state = reduceTrip(state, {
    event: "leg_stored",
    data: { index: 1, ...leg({ leg_id: 4, origin: "Tarapoto", destination: "Sauce" }) },
  });
  state = reduceTrip(state, {
    event: "leg_error",
    data: { index: 1, message: "timeout" },
  });

  expect(state.legs[1].summary).toMatchObject({ leg_id: 4, destination: "Sauce" });
  expect(state.legs[1].live).toBe(false);
  expect(state.legs[1].error).toBe("timeout");
});

test("no_route produces an empty itinerary with the message", () => {
  const state = reduceTrip(initialTripState, {
    event: "no_route",
    data: { message: "No hay una ruta conocida." },
  });

  expect(state.legs).toEqual([]);
  expect(state.noRouteMessage).toBe("No hay una ruta conocida.");
  expect(state.legsPlanned).toBe(0);
  expect(state.progress).toEqual({ done: 0, planned: 0 });
  expect(state.done).toBe(true);
});

test("progress counts refreshed and errored legs out of planned", () => {
  let state = reduceTrip(initialTripState, {
    event: "trip_started",
    data: { trip_id: 2, origin: "Iquitos", destination: "Nauta", legs_planned: 3 },
  });
  expect(state.progress).toEqual({ done: 0, planned: 3 });

  state = reduceTrip(state, { event: "leg_stored", data: { index: 0, ...leg({ leg_id: 1 }) } });
  state = reduceTrip(state, { event: "leg_stored", data: { index: 1, ...leg({ leg_id: 2 }) } });
  state = reduceTrip(state, { event: "leg_stored", data: { index: 2, ...leg({ leg_id: 3 }) } });
  expect(state.progress).toEqual({ done: 0, planned: 3 });

  state = reduceTrip(state, {
    event: "leg_refreshed",
    data: { index: 0, ...leg({ leg_id: 1, version: { ...version(10), operator: "LATAM" } }) },
  });
  expect(state.progress).toEqual({ done: 1, planned: 3 });

  state = reduceTrip(state, {
    event: "leg_error",
    data: { index: 1, message: "timeout" },
  });
  expect(state.progress).toEqual({ done: 2, planned: 3 });
  expect(state.legs.map((item) => item.index)).toEqual([0, 1, 2]);
  expect(state.legs[1].summary?.leg_id).toBe(2);

  state = reduceTrip(state, {
    event: "leg_refreshed",
    data: { index: 0, ...leg({ leg_id: 1, version: { ...version(11), operator: "Sky" } }) },
  });
  expect(state.progress).toEqual({ done: 2, planned: 3 });
  expect(state.legs[0].live).toBe(true);
  expect(state.legs[0].summary?.version.operator).toBe("Sky");

  state = reduceTrip(state, { event: "trip_done", data: { legs: 3 } });
  expect(state.done).toBe(true);
  expect(state.legs).toHaveLength(3);
  expect(state.progress).toEqual({ done: 2, planned: 3 });
});

test("parseSse splits events across chunk boundaries", () => {
  const first = parseSse('event: trip_started\ndata: {"trip_id":1,"origin":"Cusco","dest');
  expect(first.events).toEqual([]);
  expect(first.rest.startsWith("event: trip_started")).toBe(true);

  const second = parseSse(
    `${first.rest}ination":"Aguas Calientes","legs_planned":2}\n\n` +
      'event: no_route\ndata: {"message":"No hay ruta"}\n\n',
  );

  expect(second.rest).toBe("");
  expect(second.events).toEqual([
    {
      event: "trip_started",
      data: {
        trip_id: 1,
        origin: "Cusco",
        destination: "Aguas Calientes",
        legs_planned: 2,
      },
    },
    { event: "no_route", data: { message: "No hay ruta" } },
  ]);
});
