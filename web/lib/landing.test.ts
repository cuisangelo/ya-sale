import { expect, test } from "vitest";
import type { Usage } from "./api";
import { limaToday, tripHref, usageStats } from "./landing";

const TODAY = "2026-10-17";

test("tripHref builds the trip URL with trimmed, encoded params", () => {
  expect(tripHref({ origin: "  Cusco ", destination: "Aguas Calientes", date: "2026-10-25" }, TODAY)).toEqual({
    ok: true,
    href: "/viaje/?o=Cusco&d=Aguas+Calientes&f=2026-10-25",
  });
});

test("tripHref accepts today as the departure date", () => {
  expect(tripHref({ origin: "Lima", destination: "Sauce", date: TODAY }, TODAY)).toMatchObject({ ok: true });
});

test.each([
  [{ origin: " ", destination: "Nauta", date: TODAY }, "Escribe de dónde sales."],
  [{ origin: "Iquitos", destination: "", date: TODAY }, "Escribe a dónde vas."],
  [{ origin: "Arequipa", destination: " arequipa ", date: TODAY }, "El origen y el destino son el mismo lugar."],
  [{ origin: "Lima", destination: "Sauce", date: "" }, "Elige la fecha de salida."],
  [{ origin: "Lima", destination: "Sauce", date: "25/10/2026" }, "Elige la fecha de salida."],
  [{ origin: "Lima", destination: "Sauce", date: "2026-10-16" }, "La fecha de salida ya pasó."],
])("tripHref rejects %j", (draft, error) => {
  expect(tripHref(draft, TODAY)).toEqual({ ok: false, error });
});

test("limaToday uses the Lima calendar day, not UTC", () => {
  expect(limaToday(new Date("2026-10-18T03:30:00Z"))).toBe("2026-10-17");
  expect(limaToday(new Date("2026-10-18T05:30:00Z"))).toBe("2026-10-18");
});

const usage: Usage = { trips: 204, destinations: 87, people: 0, confirmed_legs: 12, recent: [] };

test("usageStats shows nothing until real numbers arrive", () => {
  expect(usageStats({ status: "loading" })).toBeNull();
  expect(usageStats({ status: "failed" })).toBeNull();
});

test("usageStats shows the four API numbers as they are, zeros included", () => {
  expect(usageStats({ status: "ready", usage })).toEqual([
    { value: "204", label: "viajes armados", tone: "land" },
    { value: "87", label: "destinos distintos", tone: "air" },
    { value: "0", label: "personas distintas", tone: "water" },
    { value: "12", label: "tramos confirmados", tone: "rail" },
  ]);
});
