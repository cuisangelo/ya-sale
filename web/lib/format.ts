import type { LegSlot, LegSummary, Mode, Option, Version } from "./api";

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
  bus: "/textil/modo-bus.svg",
  bus_urbano: "/textil/modo-bus.svg",
  custer: "/textil/modo-bus.svg",
  avion: "/textil/modo-avion.svg",
  tren: "/textil/modo-tren.svg",
  metro: "/textil/modo-tren.svg",
  colectivo: "/textil/modo-colectivo.svg",
  combi: "/textil/modo-combi.svg",
  mototaxi: "/textil/modo-mototaxi.svg",
  moto: "/textil/modo-mototaxi.svg",
  lancha: "/textil/modo-lancha.svg",
  bote: "/textil/modo-lancha.svg",
  balsa: "/textil/modo-lancha.svg",
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
