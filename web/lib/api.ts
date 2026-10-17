export type Mode =
  | "bus"
  | "avion"
  | "tren"
  | "colectivo"
  | "combi"
  | "custer"
  | "bus_urbano"
  | "metro"
  | "mototaxi"
  | "moto"
  | "lancha"
  | "bote"
  | "balsa";

export type LegStatus = "extracted" | "confirmed" | "disputed";

export interface Version {
  id: number;
  departure_point: string | null;
  operator: string | null;
  price_min_pen: string | null;
  price_max_pen: string | null;
  duration_min: number | null;
  schedule_note: string | null;
  purchase_url: string | null;
  source_url: string;
  fetched_at: string;
  confirmations: number;
}

export interface Option {
  departure_point: string | null;
  operator: string | null;
  price_min_pen: string | null;
  price_max_pen: string | null;
  duration_min: number | null;
  schedule_note: string | null;
  purchase_url: string | null;
  source_url: string;
  fetched_at: string;
}

export interface Hop {
  origin: string;
  destination: string;
  modes: Mode[];
}

export interface MapPoint {
  name: string;
  lat: number;
  lng: number;
}

export interface LegSummary {
  leg_id: number;
  mode: Mode;
  origin: string;
  destination: string;
  status: LegStatus;
  version: Version;
}

export interface LegSlot {
  index: number;
  mode: Mode;
  summary: LegSummary | null;
  options: Option[];
  live: boolean;
  error: string | null;
}

export interface TripState {
  tripId: number | null;
  origin: string;
  destination: string;
  legsPlanned: number;
  hops: Hop[];
  points: MapPoint[];
  legs: LegSlot[];
  noRouteMessage: string | null;
  done: boolean;
  progress: { done: number; planned: number };
}

export type TripSseEvent =
  | {
      event: "trip_started";
      data: { trip_id: number; origin: string; destination: string; legs_planned: number; hops: Hop[] };
    }
  | { event: "leg_stored"; data: LegEventData }
  | { event: "leg_refreshed"; data: LegEventData }
  | { event: "leg_error"; data: { index: number; mode: Mode; message: string } }
  | { event: "trip_mapped"; data: { points: MapPoint[] } }
  | { event: "no_route"; data: { message: string } }
  | { event: "trip_done"; data: { legs: number } };

type LegEventData = { index: number; options: Option[] } & LegSummary;

export interface TripRequest {
  origin: string;
  destination: string;
  date: string;
}

export interface Answer {
  text: string;
  sources: number;
  dated: number;
  confirmed: number;
}

export interface CompareResult {
  plain: Answer;
  with_tools: Answer & { legs: LegSummary[] };
}

export interface UsageEvent {
  kind: "confirmation" | "correction";
  display_name: string | null;
  mode: Mode;
  origin: string;
  destination: string;
  at: string;
}

export interface Usage {
  trips: number;
  destinations: number;
  people: number;
  confirmed_legs: number;
  recent: UsageEvent[];
}

export interface CorrectionInput {
  departure_point?: string;
  price_min_pen?: string;
  price_max_pen?: string;
  duration_min?: number;
  display_name?: string | null;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface TripStreamHandle extends AbortController {
  finished: Promise<void>;
}

const MODES: readonly Mode[] = [
  "bus",
  "avion",
  "tren",
  "colectivo",
  "combi",
  "custer",
  "bus_urbano",
  "metro",
  "mototaxi",
  "moto",
  "lancha",
  "bote",
  "balsa",
];

const STATUSES: readonly LegStatus[] = ["extracted", "confirmed", "disputed"];

const EVENT_NAMES = [
  "trip_started",
  "leg_stored",
  "leg_refreshed",
  "leg_error",
  "trip_mapped",
  "no_route",
  "trip_done",
] as const;

export const initialTripState: TripState = {
  tripId: null,
  origin: "",
  destination: "",
  legsPlanned: 0,
  hops: [],
  points: [],
  legs: [],
  noRouteMessage: null,
  done: false,
  progress: { done: 0, planned: 0 },
};

function withProgress(state: Omit<TripState, "progress">): TripState {
  // A leg that refreshed and later failed still counts once toward "k de N".
  const done = state.legs.filter((leg) => leg.live || leg.error !== null).length;
  // Every mode of every hop is refreshed on its own, so each one counts toward "k de N".
  const planned = state.hops.reduce((total, hop) => total + hop.modes.length, 0);
  return { ...state, progress: { done, planned } };
}

export function slotFor(state: TripState, index: number, mode: Mode): LegSlot | undefined {
  return state.legs.find((leg) => leg.index === index && leg.mode === mode);
}

function upsert(legs: LegSlot[], slot: LegSlot): LegSlot[] {
  const next = legs.filter((leg) => leg.index !== slot.index || leg.mode !== slot.mode);
  next.push(slot);
  next.sort((a, b) => a.index - b.index);
  return next;
}

function legSlot(data: LegEventData, live: boolean): LegSlot {
  const { index, options, ...summary } = data;
  return { index, mode: summary.mode, summary, options, live, error: null };
}

export function reduceTrip(state: TripState, event: TripSseEvent): TripState {
  switch (event.event) {
    case "trip_started":
      return withProgress({
        tripId: event.data.trip_id,
        origin: event.data.origin,
        destination: event.data.destination,
        legsPlanned: event.data.legs_planned,
        hops: event.data.hops,
        points: [],
        legs: [],
        noRouteMessage: null,
        done: false,
      });
    case "leg_stored":
      return withProgress({ ...bare(state), legs: upsert(state.legs, legSlot(event.data, false)) });
    case "leg_refreshed":
      return withProgress({ ...bare(state), legs: upsert(state.legs, legSlot(event.data, true)) });
    case "leg_error": {
      const previous = slotFor(state, event.data.index, event.data.mode);
      return withProgress({
        ...bare(state),
        legs: upsert(state.legs, {
          index: event.data.index,
          mode: event.data.mode,
          summary: previous?.summary ?? null,
          options: previous?.options ?? [],
          live: previous?.live ?? false,
          error: event.data.message,
        }),
      });
    }
    case "trip_mapped":
      return withProgress({ ...bare(state), points: event.data.points });
    case "no_route":
      return withProgress({
        ...bare(state),
        legs: [],
        hops: [],
        legsPlanned: 0,
        noRouteMessage: event.data.message,
        done: true,
      });
    case "trip_done":
      return withProgress({ ...bare(state), done: true });
    default: {
      const unexpected: never = event;
      throw new Error(`Unknown trip event: ${JSON.stringify(unexpected)}`);
    }
  }
}

function bare(state: TripState): Omit<TripState, "progress"> {
  return {
    tripId: state.tripId,
    origin: state.origin,
    destination: state.destination,
    legsPlanned: state.legsPlanned,
    hops: state.hops,
    points: state.points,
    legs: state.legs,
    noRouteMessage: state.noRouteMessage,
    done: state.done,
  };
}

export function parseSse(buffer: string): { events: TripSseEvent[]; rest: string } {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const parts = normalized.split("\n\n");
  // The tail may be an event the socket cut in half.
  const rest = parts.pop() ?? "";
  const events: TripSseEvent[] = [];
  for (const part of parts) {
    const frame = parseFrame(part);
    if (frame) events.push(frame);
  }
  return { events, rest };
}

function parseFrame(part: string): TripSseEvent | null {
  const lines = part.split("\n").map((line) => line.replace(/\r$/, ""));
  if (lines.every((line) => line.trim() === "" || line.startsWith(":"))) return null;

  let name = "";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) name = line.slice("event:".length).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice("data:".length).trim());
  }
  if (!name || dataLines.length === 0) throw new Error("Incomplete SSE frame");
  if (!EVENT_NAMES.includes(name as (typeof EVENT_NAMES)[number])) {
    throw new Error(`Unknown trip event: ${name}`);
  }
  return { event: name, data: JSON.parse(dataLines.join("\n")) } as TripSseEvent;
}

export function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}

// EventSource cannot POST a JSON body, so the trip stream is read from fetch.
export function streamTrip(body: TripRequest, onEvent: (event: TripSseEvent) => void): TripStreamHandle {
  const controller = new AbortController();
  const finished = readTripStream(body, onEvent, controller.signal);
  return Object.assign(controller, { finished });
}

async function readTripStream(
  body: TripRequest,
  onEvent: (event: TripSseEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch("/api/trips", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "text/event-stream",
    },
    body: JSON.stringify({
      origin: body.origin,
      destination: body.destination,
      date: body.date,
    }),
    signal,
  });
  if (!response.ok) throw await toApiError(response);
  if (!response.body) throw new Error("Empty trip stream");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      pending += decoder.decode(value, { stream: true });
      const parsed = parseSse(pending);
      pending = parsed.rest;
      for (const event of parsed.events) onEvent(event);
    }
    pending += decoder.decode();
    if (pending.trim() !== "") {
      const parsed = parseSse(`${pending}\n\n`);
      for (const event of parsed.events) onEvent(event);
    }
  } finally {
    reader.releaseLock();
  }
}

export function confirmLeg(
  legId: number,
  versionId: number,
  displayName: string | null,
): Promise<LegSummary> {
  return postJson(`/api/legs/${legId}/confirmations`, {
    version_id: versionId,
    display_name: displayName,
  }, parseLegSummary);
}

export function correctLeg(legId: number, input: CorrectionInput): Promise<LegSummary> {
  return postJson(`/api/legs/${legId}/corrections`, input, parseLegSummary);
}

export function compareQuestion(question: string): Promise<CompareResult> {
  return postJson("/api/compare", { question }, parseCompare);
}

export function fetchUsage(): Promise<Usage> {
  return getJson("/api/usage", parseUsage);
}

async function postJson<T>(path: string, body: unknown, parse: (value: unknown) => T): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await toApiError(response);
  return parse(await response.json());
}

async function getJson<T>(path: string, parse: (value: unknown) => T): Promise<T> {
  const response = await fetch(path, { headers: { accept: "application/json" } });
  if (!response.ok) throw await toApiError(response);
  return parse(await response.json());
}

async function toApiError(response: Response): Promise<ApiError> {
  const text = await response.text();
  return new ApiError(response.status, messageFromBody(response.status, text));
}

function messageFromBody(status: number, text: string): string {
  const trimmed = text.trim();
  if (!trimmed || trimmed.startsWith("<")) return `HTTP ${status}`;
  try {
    const body = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) return body.detail;
    if (status === 422) return "Revisa los datos e inténtalo de nuevo.";
    if (body.detail !== undefined) return JSON.stringify(body.detail);
  } catch {
    if (trimmed.length <= 280) return trimmed;
  }
  return `HTTP ${status}`;
}

export function errorText(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return fallback;
  if (error instanceof Error && error.message.trim()) return error.message;
  return fallback;
}

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`Invalid ${label}`);
  }
  return value as Record<string, unknown>;
}

function reqString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string") throw new Error(`Invalid ${key}`);
  return value;
}

function reqNumber(record: Record<string, unknown>, key: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`Invalid ${key}`);
  return value;
}

function optString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  if (value == null) return null;
  if (typeof value !== "string") throw new Error(`Invalid ${key}`);
  return value;
}

function optNumber(record: Record<string, unknown>, key: string): number | null {
  const value = record[key];
  if (value == null) return null;
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`Invalid ${key}`);
  return value;
}

function isMode(value: string): value is Mode {
  return (MODES as readonly string[]).includes(value);
}

function isStatus(value: string): value is LegStatus {
  return (STATUSES as readonly string[]).includes(value);
}

export function parseLegSummary(value: unknown): LegSummary {
  const record = asRecord(value, "leg");
  const mode = reqString(record, "mode");
  if (!isMode(mode)) throw new Error(`Invalid mode: ${mode}`);
  const status = reqString(record, "status");
  if (!isStatus(status)) throw new Error(`Invalid status: ${status}`);
  return {
    leg_id: reqNumber(record, "leg_id"),
    mode,
    origin: reqString(record, "origin"),
    destination: reqString(record, "destination"),
    status,
    version: parseVersion(record.version),
  };
}

function parseVersion(value: unknown): Version {
  const record = asRecord(value, "version");
  return {
    id: reqNumber(record, "id"),
    departure_point: optString(record, "departure_point"),
    operator: optString(record, "operator"),
    price_min_pen: optString(record, "price_min_pen"),
    price_max_pen: optString(record, "price_max_pen"),
    duration_min: optNumber(record, "duration_min"),
    schedule_note: optString(record, "schedule_note"),
    purchase_url: optString(record, "purchase_url"),
    source_url: reqString(record, "source_url"),
    fetched_at: reqString(record, "fetched_at"),
    confirmations: reqNumber(record, "confirmations"),
  };
}

function parseAnswer(value: unknown): Answer {
  const record = asRecord(value, "answer");
  return {
    text: reqString(record, "text"),
    sources: reqNumber(record, "sources"),
    dated: reqNumber(record, "dated"),
    confirmed: reqNumber(record, "confirmed"),
  };
}

function parseCompare(value: unknown): CompareResult {
  const record = asRecord(value, "compare");
  const withTools = asRecord(record.with_tools, "with_tools");
  const legs = withTools.legs;
  if (!Array.isArray(legs)) throw new Error("Invalid legs");
  return {
    plain: parseAnswer(record.plain),
    with_tools: { ...parseAnswer(record.with_tools), legs: legs.map(parseLegSummary) },
  };
}

function parseUsage(value: unknown): Usage {
  const record = asRecord(value, "usage");
  const recent = record.recent;
  if (!Array.isArray(recent)) throw new Error("Invalid recent");
  return {
    trips: reqNumber(record, "trips"),
    destinations: reqNumber(record, "destinations"),
    people: reqNumber(record, "people"),
    confirmed_legs: reqNumber(record, "confirmed_legs"),
    recent: recent.map(parseUsageEvent),
  };
}

function parseUsageEvent(value: unknown): UsageEvent {
  const record = asRecord(value, "usage event");
  const kind = reqString(record, "kind");
  if (kind !== "confirmation" && kind !== "correction") throw new Error(`Invalid kind: ${kind}`);
  const mode = reqString(record, "mode");
  if (!isMode(mode)) throw new Error(`Invalid mode: ${mode}`);
  const displayName = record.display_name;
  if (displayName !== null && typeof displayName !== "string") throw new Error("Invalid display_name");
  return {
    kind,
    display_name: displayName,
    mode,
    origin: reqString(record, "origin"),
    destination: reqString(record, "destination"),
    at: reqString(record, "at"),
  };
}
