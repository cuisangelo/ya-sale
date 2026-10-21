import { departuresFor, slotFor, type Departure, type Mode, type Schedule, type TravelerPreferences, type TripState } from "./api";
import { departureClock, formatPrice, modeLabel, summarySourceLine } from "./format";

export interface Advice {
  hop: string;
  title: string;
  detail: string;
  link: string | null;
}

const SCHEDULE_LABELS: Record<Schedule, string> = { day: "de día", night: "de noche" };

export function preferenceLabels(preferences: TravelerPreferences): string[] {
  const labels: string[] = [];
  if (preferences.schedule) labels.push(`Salir ${SCHEDULE_LABELS[preferences.schedule]}`);
  if (preferences.cheapest) labels.push("Precio más bajo");
  return labels;
}

// Night runs 19:00–05:59 in Lima, so every departure is either day or night.
function inSchedule(departure: Departure, schedule: Schedule): boolean {
  const hour = Number(departureClock(departure.departs_at).slice(0, 2));
  const night = hour >= 19 || hour < 6;
  return schedule === "night" ? night : !night;
}

function departureDetail(departure: Departure): string {
  const price = departure.price_pen == null ? null : formatPrice(departure.price_pen, null);
  return [departureClock(departure.departs_at), departure.operator, price].filter(Boolean).join(" · ");
}

function earliest(departures: Departure[]): Departure {
  return departures.reduce((best, next) => (Date.parse(next.departs_at) < Date.parse(best.departs_at) ? next : best));
}

function cheapestDeparture(departures: Departure[]): Departure | null {
  const priced = departures.filter((departure) => departure.price_pen != null);
  if (priced.length === 0) return null;
  return priced.reduce((best, next) => (Number(next.price_pen) < Number(best.price_pen) ? next : best));
}

/**
 * Points each hop at the published departure or mode that fits what the traveler saved.
 * It only picks among facts already on the page, so every line keeps its source and date.
 */
export function routeAdvice(state: TripState, selectedModes: Mode[], preferences: TravelerPreferences): Advice[] {
  const advice: Advice[] = [];
  const schedule = preferences.schedule;
  state.hops.forEach((hop, index) => {
    const name = `${hop.origin} → ${hop.destination}`;
    const mode = selectedModes[index] ?? hop.modes[0];
    const open = departuresFor(state, index, mode).filter((departure) => departure.seats_available !== 0);

    if (schedule && open.length > 0) {
      const fitting = open.filter((departure) => inSchedule(departure, schedule));
      const when = SCHEDULE_LABELS[schedule];
      if (fitting.length > 0) {
        const pick = earliest(fitting);
        advice.push({ hop: name, title: `Primera salida ${when}`, detail: departureDetail(pick), link: pick.booking_url });
      } else {
        const count = open.length === 1 ? "la salida publicada" : `las ${open.length} salidas publicadas`;
        advice.push({ hop: name, title: `Ninguna salida ${when}`, detail: `Revisamos ${count} para tu fecha.`, link: null });
      }
    }

    if (preferences.cheapest) {
      const pick = cheapestDeparture(open);
      if (pick) {
        advice.push({ hop: name, title: "La salida más barata", detail: departureDetail(pick), link: pick.booking_url });
        return;
      }
      const byMode = cheapestMode(state, index, hop.modes);
      if (byMode) advice.push({ hop: name, ...byMode, link: null });
    }
  });
  return advice;
}

// Without departures, a hop with several modes is compared on each mode's saved, dated fare.
function cheapestMode(state: TripState, index: number, modes: Mode[]): { title: string; detail: string } | null {
  if (modes.length < 2) return null;
  const priced = modes.flatMap((mode) => {
    const summary = slotFor(state, index, mode)?.summary;
    const floor = summary ? (summary.version.price_min_pen ?? summary.version.price_max_pen) : null;
    return summary && floor != null ? [{ summary, floor: Number(floor) }] : [];
  });
  if (priced.length < 2) return null;
  const best = priced.reduce((left, right) => (right.floor < left.floor ? right : left)).summary;
  const price = formatPrice(best.version.price_min_pen, best.version.price_max_pen);
  return { title: `Más barato en ${modeLabel(best.mode).toLowerCase()}`, detail: `${price} · ${summarySourceLine(best)}` };
}
