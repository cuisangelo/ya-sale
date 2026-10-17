# API contract

Owned by the backend; the web frontend consumes exactly this. All paths are same-origin (the
backend serves the static web export at `/`). JSON field names are `snake_case`. Timestamps are
ISO 8601 UTC strings. Money is soles (PEN) as decimal strings (`"12.50"`) or `null`.

## Shared types

```ts
type Mode = "bus" | "avion" | "tren" | "colectivo" | "combi" | "custer" | "bus_urbano"
          | "metro" | "mototaxi" | "moto" | "lancha" | "bote" | "balsa";
type LegStatus = "extracted" | "confirmed" | "disputed";   // UI: Extraído · Confirmado · En disputa

interface Version {
  id: number;
  departure_point: string | null;
  operator: string | null;
  price_min_pen: string | null;
  price_max_pen: string | null;
  duration_min: number | null;
  schedule_note: string | null;
  purchase_url: string | null;
  source_url: string;             // "ya-sale:confirmation" when a person entered it
  fetched_at: string;
  confirmations: number;
}

interface Option {                // one offer a page lists for the leg; read-only, never confirmed
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

interface Hop {
  origin: string;
  destination: string;
  modes: Mode[];                  // modes[0] is the main way; the rest are alternatives the pages name (max 2 in total)
}

interface MapPoint { name: string; lat: number; lng: number; }

interface Departure {
  operator: string;
  departs_at: string;             // ISO 8601 in Lima time, e.g. "2026-10-25T19:30:00-05:00"
  arrives_at: string | null;
  price_pen: string | null;       // decimal as string, like Version prices
  seats_available: number | null;
  booking_url: string;            // that departure's own page (seat selection), not a home page or a results list
  seller: string;                 // the domain that sells it, e.g. "movilbus.pe"
}

interface LegSummary {
  leg_id: number;
  mode: Mode;
  origin: string;
  destination: string;
  status: LegStatus;
  version: Version;               // the version to display: newest, or the confirmed one if newer ones match it
}
```

## `POST /api/trips` (Server-Sent Events)

Request: `{"origin": "Cusco", "destination": "Aguas Calientes", "date": "2026-10-25"}`.
Response: `text/event-stream`; each message is `event: <name>\ndata: <json>\n\n`.

| event | data | meaning |
|---|---|---|
| `trip_started` | `{trip_id, origin, destination, legs_planned, hops: Hop[]}` | always first, unless `no_route` |
| `leg_stored` | `{index} & LegSummary & {options: Option[]}` | a saved version, shown immediately ("guardado [fecha] · refrescando…") |
| `leg_refreshed` | `{index} & LegSummary & {options: Option[]}` | live data arrived ("actualizado hace N s"); replaces the same `index` and `mode` |
| `leg_error` | `{index, mode, message}` | live refresh of that mode failed; keep the stored leg if any |
| `leg_departures` | `{index, mode, departures: Departure[]}` | concrete departures on sale for the trip `date` on a bus hop, earliest first; only sent when a seller found some, so the scraped `options` stay as the fallback |
| `trip_mapped` | `{points: MapPoint[]}` | the places of `hops` that were found on the map; a missing place is left out, never guessed |
| `no_route` | `{message}` | the only event; show `message` (Spanish) and no legs |
| `trip_done` | `{legs}` | always last |

`index` is the 0-based position of the hop in the trip; a hop has one leg per mode in `hops[index].modes`.
`legs_planned` counts hops. Progress = refreshed or errored `(index, mode)` legs out of all modes of all
hops. `options` are sorted cheapest priced first, at most 10. Errors: `422` invalid body, `429 {"detail": "..."}` rate limit.

## `GET /api/legs/{leg_id}`

`200 {leg_id, mode, origin, destination, status, versions: Version[]}` (oldest first). `404`.

## `POST /api/legs/{leg_id}/confirmations`

Request `{"version_id": 7, "display_name": "Ana" | null}` → `201 LegSummary`.
`409 {"detail": "Ya confirmaste este tramo."}` when the same person confirmed that version.

## `POST /api/legs/{leg_id}/corrections`

Request `{"departure_point"?, "price_min_pen"?, "price_max_pen"?, "duration_min"?, "display_name"?}`
→ `201 LegSummary` (a new confirmed version; the leg may become `disputed`).

## `GET /api/usage`

`200 {trips, destinations, people, confirmed_legs, recent: [{kind: "confirmation" | "correction",
display_name: string | null, mode, origin, destination, at}]}` (recent: newest first, max 10).

## `POST /api/compare`

Request `{"question": "Quiero ir de Lima a Sauce sin tour..."}` →
`200 {plain: Answer, with_tools: Answer & {legs: LegSummary[]}}` where
`Answer = {text: string, sources: number, dated: number, confirmed: number}`.

## MCP

Streamable HTTP at `/mcp` with tools `plan_trip(origin, destination, date)`,
`get_leg(leg_id)`, `confirm_leg(leg_id, version_id, display_name?)`.
