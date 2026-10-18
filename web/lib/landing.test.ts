import { expect, test, vi } from "vitest";
import type { RecentTrip } from "./api";
import { buildRecentSearches, limaToday, tripHref } from "./landing";

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

function recentTrip(origin: string, destination: string): RecentTrip {
  return { origin, destination, place: destination, at: "2026-10-17T14:00:00Z", lat: -6.42, lng: -77.92 };
}

test("buildRecentSearches skips and logs a search that is not a valid trip, keeping the rest", () => {
  const log = vi.spyOn(console, "error").mockImplementation(() => {});
  const searches = buildRecentSearches(
    [recentTrip("Lima", "lima"), recentTrip("Lima", "Kuélap"), recentTrip("Ica", "Huacachina")],
    TODAY,
  );
  expect(searches).toEqual([
    { trip: recentTrip("Lima", "Kuélap"), href: "/viaje/?o=Lima&d=Ku%C3%A9lap&f=2026-10-17" },
    { trip: recentTrip("Ica", "Huacachina"), href: "/viaje/?o=Ica&d=Huacachina&f=2026-10-17" },
  ]);
  expect(log).toHaveBeenCalledTimes(1);
  log.mockRestore();
});
