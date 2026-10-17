import type { RecentTrip } from "./api";

export interface TripDraft {
  origin: string;
  destination: string;
  date: string;
}

export interface RecentSearch {
  trip: RecentTrip;
  href: string;
}

export type TripHrefResult = { ok: true; href: string } | { ok: false; error: string };

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

// `today` comes from the caller so validation follows the visitor's Lima day, not the build's.
export function tripHref(draft: TripDraft, today: string): TripHrefResult {
  const origin = draft.origin.trim();
  const destination = draft.destination.trim();
  const date = draft.date.trim();
  if (!origin) return { ok: false, error: "Escribe de dónde sales." };
  if (!destination) return { ok: false, error: "Escribe a dónde vas." };
  if (origin.toLocaleLowerCase("es") === destination.toLocaleLowerCase("es")) {
    return { ok: false, error: "El origen y el destino son el mismo lugar." };
  }
  if (!ISO_DATE.test(date)) return { ok: false, error: "Elige la fecha de salida." };
  // ISO dates compare correctly as strings.
  if (date < today) return { ok: false, error: "La fecha de salida ya pasó." };
  const params = new URLSearchParams({ o: origin, d: destination, f: date });
  return { ok: true, href: `/viaje/?${params}` };
}

export function limaToday(now: Date): string {
  // en-CA formats dates as YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Lima" }).format(now);
}

// Any visitor's input lands in the recent list, so one unusable search is logged and skipped
// instead of blanking the home for everyone.
export function buildRecentSearches(trips: RecentTrip[], today: string): RecentSearch[] {
  return trips.flatMap((trip) => {
    const result = tripHref({ origin: trip.origin, destination: trip.destination, date: today }, today);
    if (result.ok) return [{ trip, href: result.href }];
    console.error(`Skipping recent search ${trip.origin} → ${trip.destination}: ${result.error}`);
    return [];
  });
}
