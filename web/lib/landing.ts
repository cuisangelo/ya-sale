import type { Usage } from "./api";
import { formatCount, type ModeTone } from "./format";

export interface TripDraft {
  origin: string;
  destination: string;
  date: string;
}

export type TripHrefResult = { ok: true; href: string } | { ok: false; error: string };

export type UsageState = { status: "loading" } | { status: "ready"; usage: Usage } | { status: "failed" };

export interface UsageStat {
  value: string;
  label: string;
  tone: ModeTone;
}

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

export function usageStats(state: UsageState): UsageStat[] | null {
  if (state.status !== "ready") return null;
  const { usage } = state;
  return [
    { value: formatCount(usage.trips), label: "viajes armados", tone: "land" },
    { value: formatCount(usage.destinations), label: "destinos distintos", tone: "air" },
    { value: formatCount(usage.people), label: "personas distintas", tone: "water" },
    { value: formatCount(usage.confirmed_legs), label: "tramos confirmados", tone: "rail" },
  ];
}
