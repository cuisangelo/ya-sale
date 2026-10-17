import { departuresFor, type LegSlot, type LegSummary, type Mode, type Option, type TripState, type Version } from "./api";

const MODE_LABELS: Record<Mode, string> = {
  bus: "Bus",
  avion: "Avión",
  tren: "Tren",
  colectivo: "Colectivo",
  combi: "Combi",
  custer: "Custer",
  bus_urbano: "Bus urbano",
  metro: "Metro",
  mototaxi: "Mototaxi",
  moto: "Moto",
  lancha: "Lancha",
  bote: "Bote",
  balsa: "Balsa",
};

const MODE_ICONS: Record<string, string> = {
  bus: "/modes/bus.svg",
  bus_urbano: "/modes/bus.svg",
  custer: "/modes/bus.svg",
  avion: "/modes/avion.svg",
  tren: "/modes/tren.svg",
  metro: "/modes/tren.svg",
  colectivo: "/modes/colectivo.svg",
  combi: "/modes/combi.svg",
  mototaxi: "/modes/mototaxi.svg",
  moto: "/modes/mototaxi.svg",
  lancha: "/modes/lancha.svg",
  bote: "/modes/lancha.svg",
  balsa: "/modes/lancha.svg",
};

export type ModeTone = "land" | "air" | "rail" | "water";

export function modeLabel(mode: string): string {
  return MODE_LABELS[mode as Mode] ?? mode;
}

export function modeIconSrc(mode: string): string | null {
  return MODE_ICONS[mode] ?? null;
}

export function modeTone(mode: string): ModeTone {
  if (mode === "avion") return "air";
  if (mode === "tren" || mode === "metro") return "rail";
  if (mode === "lancha" || mode === "bote" || mode === "balsa") return "water";
  return "land";
}

export function formatDate(iso: string): string {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return iso;
  return new Intl.DateTimeFormat("es-PE", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "America/Lima",
  }).format(then);
}

export function departureClock(iso: string): string {
  return new Intl.DateTimeFormat("es-PE", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "America/Lima",
  }).format(Date.parse(iso));
}

// Only hop 0 says when the trip leaves; a later hop's bus would pass for the trip's departure.
export function firstDeparture(state: TripState, firstMode: Mode | undefined): { time: string; operator: string } | null {
  if (!firstMode) return null;
  const departures = departuresFor(state, 0, firstMode);
  if (departures.length === 0) return null;
  const earliest = departures.reduce((best, next) => (Date.parse(next.departs_at) < Date.parse(best.departs_at) ? next : best));
  return { time: departureClock(earliest.departs_at), operator: earliest.operator };
}

// The trip date is a calendar day with no zone; read at noon UTC it is the same day everywhere.
export function departuresHeading(day: string): string {
  const label = new Intl.DateTimeFormat("es-PE", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(Date.parse(`${day}T12:00:00Z`));
  return `Salidas del ${label.replace(",", "")}`;
}

// Shape alone lets `2026-13-01` through, and formatting it throws.
export function isTripDay(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T12:00:00Z`));
}

export function tripDayLabel(day: string): string {
  return new Intl.DateTimeFormat("es-PE", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" })
    .format(Date.parse(`${day}T12:00:00Z`))
    .replace(/[,.]/g, "");
}

export function seatsLabel(seats: number | null): string | null {
  if (seats == null) return null;
  if (seats === 0) return "agotado";
  return seats === 1 ? "1 asiento libre" : `${seats} asientos libres`;
}

export function relativeTime(iso: string, now: number): string {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return iso;
  const minutes = Math.floor((now - then) / 60000);
  if (minutes < 1) return "hace un momento";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return `hace ${Math.floor(hours / 24)} d`;
}

export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} min`;
  if (rest === 0) return `${hours} h`;
  return `${hours} h ${rest} min`;
}

function toCents(value: string): number | null {
  if (!/^\d+(\.\d{1,2})?$/.test(value)) return null;
  const [whole, frac = ""] = value.split(".");
  return Number(whole) * 100 + Number(frac.padEnd(2, "0").slice(0, 2));
}

function fromCents(amount: number): string {
  const whole = Math.trunc(amount / 100);
  const frac = Math.abs(amount % 100);
  if (frac === 0) return String(whole);
  return `${whole}.${String(frac).padStart(2, "0")}`;
}

export function formatPrice(min: string | null, max: string | null): string | null {
  const left = min == null ? null : formatSoles(min);
  const right = max == null ? null : formatSoles(max);
  if (left && right && left !== right) return `S/${left}–${right}`;
  const single = left ?? right;
  return single == null ? null : `S/${single}`;
}

function formatSoles(value: string): string {
  const cents = toCents(value);
  return cents == null ? value : fromCents(cents);
}

export function legFactParts(version: Version): string[] {
  const parts: string[] = [];
  if (version.operator) parts.push(version.operator);
  if (version.schedule_note) parts.push(version.schedule_note);
  if (version.departure_point) parts.push(`Sale de ${version.departure_point}`);
  const price = formatPrice(version.price_min_pen, version.price_max_pen);
  if (price) parts.push(price);
  if (version.duration_min != null) parts.push(formatDuration(version.duration_min));
  return parts;
}

export function purchaseUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.href;
  } catch {
    return null;
  }
}

export function sourceLabel(sourceUrl: string): string {
  try {
    const url = new URL(sourceUrl);
    if (url.protocol === "http:" || url.protocol === "https:") return url.host;
  } catch {
    return sourceUrl;
  }
  return sourceUrl;
}

// Operators that sell on their own site; matched as whole words so "Movil" never matches "Automovil".
const OPERATOR_SITES: [string, string][] = [
  ["latam", "https://www.latamairlines.com/pe/es"],
  ["sky airline", "https://www.skyairline.com/peru"],
  ["jetsmart", "https://jetsmart.com/pe/es/"],
  ["star peru", "https://www.starperu.com/"],
  ["cruz del sur", "https://www.cruzdelsur.com.pe/"],
  ["oltursa", "https://www.oltursa.pe/"],
  ["civa", "https://www.civa.com.pe/"],
  ["movil", "https://www.movilbus.pe/"],
  ["peru rail", "https://www.perurail.com/"],
  ["perurail", "https://www.perurail.com/"],
  ["inca rail", "https://incarail.com/"],
];

function words(text: string): string {
  return ` ${text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()} `;
}

function operatorSite(operator: string | null): string | null {
  if (!operator) return null;
  const name = words(operator);
  return OPERATOR_SITES.find(([key]) => name.includes(` ${key} `))?.[1] ?? null;
}

export function optionLink(option: Pick<Option, "operator" | "purchase_url" | "source_url">): string | null {
  return purchaseUrl(option.purchase_url) ?? operatorSite(option.operator) ?? purchaseUrl(option.source_url);
}

export interface TripDay {
  origin: string;
  destination: string;
  date: string; // YYYY-MM-DD
}

// Airports SKY flies to in Peru; a town without its own airport keeps the plain link.
const AIRPORTS: Record<string, string> = {
  lima: "LIM",
  arequipa: "AQP",
  cusco: "CUZ",
  trujillo: "TRU",
  piura: "PIU",
  chiclayo: "CIX",
  iquitos: "IQT",
  tarapoto: "TPP",
  juliaca: "JUL",
  tacna: "TCQ",
  "puerto maldonado": "PEM",
  pucallpa: "PCL",
  cajamarca: "CJA",
  tumbes: "TBP",
  ayacucho: "AYP",
};

function kuposCity(name: string): string {
  return `${words(name).trim().replace(/ /g, "-")},peru`;
}

// kupos and Civa (which runs on kupos) open a filled search from the URL, and SKY a flight search.
export function datedLink(link: string | null, trip: TripDay): string | null {
  if (!link) return null;
  const host = new URL(link).host.replace(/^www\./, "");
  const [year, month, day] = trip.date.split("-");
  if (host === "kupos.pe" || host === "civa.com.pe") {
    const site = host === "kupos.pe" ? "https://kupos.pe" : "https://www.civa.com.pe";
    return `${site}/es/pasajes-bus/${kuposCity(trip.origin)}/${kuposCity(trip.destination)}?date_onward=${day}-${month}-${year}`;
  }
  const from = AIRPORTS[words(trip.origin).trim()];
  const to = AIRPORTS[words(trip.destination).trim()];
  if (host.endsWith("skyairline.com") && from && to) {
    return `https://initial-sale.skyairline.com/es/peru?origin=${from}&destination=${to}&departureDate=${trip.date}&arrivalDate=${trip.date}&flightType=OW&ADT=1`;
  }
  return link;
}

// The logo always names the site the link opens, so the row never promises one site and opens another.
export function logoDomain(link: string | null): string | null {
  if (!link) return null;
  return new URL(link).host.replace(/^www\./, "");
}

export function logoSrc(domain: string): string {
  return `/logos/${domain}.png`;
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
}

function secondsAgo(iso: string, now: number): number {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return 0;
  return Math.max(0, Math.round((now - then) / 1000));
}

export function freshnessLine(slot: LegSlot, now: number): string {
  const summary = slot.summary;
  if (!summary) return "";
  const saved = formatDate(summary.version.fetched_at);
  if (!slot.live) {
    return slot.error ? `guardado ${saved} · no se pudo actualizar` : `guardado ${saved} · refrescando…`;
  }
  return liveSourceLine(summary, saved, now);
}

export function summarySourceLine(summary: LegSummary): string {
  const saved = formatDate(summary.version.fetched_at);
  const version = summary.version;
  if (version.source_url === "ya-sale:confirmation" || summary.status === "confirmed") {
    const count = version.confirmations;
    if (count <= 0) return `confirmado · ${saved}`;
    const who = count === 1 ? "1 persona" : `${count} personas`;
    return `confirmado por ${who} · ${saved}`;
  }
  return `según ${sourceLabel(version.source_url)} · ${saved}`;
}

function liveSourceLine(summary: LegSummary, saved: string, now: number): string {
  const version = summary.version;
  if (version.source_url === "ya-sale:confirmation" || summary.status === "confirmed") {
    const count = version.confirmations;
    if (count <= 0) return `confirmado · ${saved}`;
    const who = count === 1 ? "1 persona" : `${count} personas`;
    return `confirmado por ${who} · ${saved}`;
  }
  return `según ${sourceLabel(version.source_url)} · actualizado hace ${secondsAgo(version.fetched_at, now)} s`;
}

export interface ItineraryTotals {
  price: string | null;
  duration: string | null;
}

/** Totals over one leg per hop; unknown as soon as one leg lacks the value, never a partial sum. */
export function itineraryTotals(legs: LegSlot[]): ItineraryTotals {
  return { price: totalPrice(legs), duration: totalDuration(legs) };
}

function totalDuration(legs: LegSlot[]): string | null {
  if (legs.length === 0) return null;
  let total = 0;
  for (const leg of legs) {
    const minutes = leg.summary?.version.duration_min;
    if (minutes == null) return null;
    total += minutes;
  }
  return formatDuration(total);
}

function totalPrice(legs: LegSlot[]): string | null {
  if (legs.length === 0) return null;
  let min = 0;
  let max = 0;
  for (const leg of legs) {
    const version = leg.summary?.version;
    if (!version) return null;
    const low = version.price_min_pen == null ? null : toCents(version.price_min_pen);
    const high = version.price_max_pen == null ? null : toCents(version.price_max_pen);
    if (low == null && high == null) return null;
    min += low ?? high ?? 0;
    max += high ?? low ?? 0;
  }
  return formatPrice(fromCents(min), min === max ? null : fromCents(max));
}

export function priceFloor(version: Version, options: Option[]): string | null {
  const cents = [version, ...options]
    .flatMap((offer) => [offer.price_min_pen, offer.price_max_pen])
    .map((value) => (value == null ? null : toCents(value)))
    .filter((value): value is number => value != null);
  if (cents.length === 0) return null;
  return `desde S/${fromCents(Math.min(...cents))}`;
}

export function mapsDirectionsUrl(place: string, town: string): string {
  const url = new URL("https://www.google.com/maps/dir/");
  url.searchParams.set("api", "1");
  url.searchParams.set("destination", `${place}, ${town}, Perú`);
  return url.href;
}

export function columnCounter(sources: number, dated: number): string {
  const when = dated === 0 ? "sin fecha" : `${dated} con fecha`;
  return `${sources} fuentes · ${when}`;
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat("es-PE").format(value);
}
