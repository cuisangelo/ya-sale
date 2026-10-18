# Photo-first redesign of Ya Sale (home + trip view) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ya Sale looks modern and its own: a real photo of the destination on every trip and on the home page, the useful numbers first, carmine as the only accent, one typeface in three sizes.

**Architecture:** The backend records each trip's resolved destination (name and point) while the SSE stream runs, and exposes the latest routed searches at `GET /api/trips/recent`. The web gets new design tokens, Inter, a photo adapter (`web/lib/photos.ts`, Wikipedia/Commons from the browser, like `roads.ts`) and one shared `DestinationHero`. The home and trip screens are rebuilt on those pieces. `/comparar` and `/uso` only inherit the tokens.

**Tech Stack:** FastAPI + psycopg (Postgres) + pytest in `docker compose`; Next.js 15 static export, React 19, plain CSS / CSS Modules, Leaflet, vitest; pnpm, uv.

**Spec:** `docs/superpowers/specs/2026-10-17-rediseno-frontend-design.md`. The mockups are in `docs/superpowers/specs/2026-10-17-rediseno/inicio.html` (bottom half) and `viaje.html`.

## Global Constraints

- **Accent and palette:**
  - accent `#C8102E` (`--acc`), `--acc-soft: #FBE7EA`;
  - `--ink: #111114`, `--mute: #6B6B76`, `--line: #ECECF0`, `--soft: #F6F6F8`;
  - background `#FFFFFF`;
  - no other hues anywhere: no mode tone colors, no textile palette.
- **Font sizes:** only `40px`, `18px` and `14px` in every CSS file. `32px` is allowed only for the hero title under `@media (max-width: 640px)`. Hierarchy comes from weight (400/600/700/800) and color.
- **One typeface:** Inter, self-hosted `.woff2` in `web/app/fonts/`. Bricolage, Archivo and JetBrains Mono are removed.
- **No cultural motifs:** `Franja`, chakana, mayu, chaska, `logo-inti.svg` and `public/textil/*` must not be used anywhere.
- **Photo credits:** every photo shown carries its author, license and a link to its Commons page.
- **Text over photos:** always on the dark gradient `linear-gradient(180deg, rgba(0,0,0,.45), rgba(0,0,0,.05) 40%, rgba(0,0,0,.75))`.
- **Motion:** every animation has a `prefers-reduced-motion: reduce` override that turns it off.
- **Copy:** UI copy in Spanish; code, identifiers and commits in English (AGENTS.md).
- **No new npm or Python dependencies.**
- **Fail loud, with one exception:** the photo adapter's failure has a designed visible state (gradient hero) plus a `console.error`.
- **Untouched:** the SSE event flow, the confirmations and the corrections keep their behavior.
- **Logging:** every task appends its `BITACORA.md` entry in Spanish (format in AGENTS.md) in the same commit.
- **Commands:**
  - backend tests: `docker compose run --rm backend uv run pytest -q`;
  - web: `cd web && pnpm exec tsc --noEmit && pnpm test`.

## Review Focus

1. **Place names with accents, spaces or parentheses** ("Kuélap", "Sauce (Perú)") must be URL-encoded in every Wikipedia/Commons request and still find the photo. Pinned in Task 3.
2. **A Wikipedia title that exists but isn't the place** must never supply the photo: a disambiguation page, a page with no coordinates, or the food "Sauce" more than 25 km away. Pinned in Task 3.
3. **`localStorage` that throws** (private window, blocked storage) must still yield the photo from the network. Pinned in Task 3.
4. **A trip whose last stop the planner could not locate,** or a `no_route` trip, must leave `resolved_destination` NULL and stay out of `/api/trips/recent`. Pinned in Task 1.
5. **A first leg with no departures** must hide "Primera salida" instead of borrowing a later leg's bus. Pinned in Task 6.

---

### Task 1: Backend — resolved destination per trip and `GET /api/trips/recent`

**Files:**
- Modify: `backend/app/schema.sql` (after the `trips` table)
- Modify: `backend/app/usage/repository.py`
- Modify: `backend/app/api/routes.py` (`create_trip` stream, new route)
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Produces:
  - `UsageRepository.resolve_trip(trip_id: int, place: str, lat: float, lng: float) -> None`;
  - `UsageRepository.recent_trips() -> list[dict]`;
  - `GET /api/trips/recent` returns
    `[{"origin": str, "destination": str, "place": str, "at": iso8601 str, "lat": float, "lng": float}]`.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_api.py`.

  Make `FakePlanner` configurable through a `points` constructor argument (default: Cusco plus the final stop `MapPoint("Ollantaytambo", -13.26, -72.26)`). Then add:

  ```python
  async def test_recent_lists_routed_trips_with_their_resolved_place(api):
      await stream_trip(api, headers(ip="203.0.113.7"))
      body = (await api.get("/api/trips/recent")).json()
      assert body == [{"origin": "Cusco", "destination": "Aguas Calientes", "place": "Ollantaytambo",
                       "at": body[0]["at"], "lat": -13.26, "lng": -72.26}]
      assert "fingerprint" not in body[0]

  async def test_recent_skips_trips_whose_last_stop_was_not_located(api_without_final_point): ...
      # fixture api_without_final_point = the `api` fixture built with FakePlanner(legs, points=(MapPoint("Cusco", -13.53, -71.97),));
      # the TripMapped event carries only Cusco → resolved_destination stays NULL → []

  async def test_recent_dedupes_case_insensitively_keeps_newest_and_caps_at_8(api, pool): ...
      # insert 10 routed trips directly (two differ only in case) → 8 items, newest first, one per pair

  async def test_recent_excludes_team_fingerprints(api, pool): ...
      # routed trip with fingerprint "team-fp" → []
  ```

  `stream_trip` posts `BODY` to `/api/trips` and reads the whole stream. Reuse the existing helper if `test_api.py` already has one.
- [ ] **Step 2: Run the tests and confirm they fail.**
  Run: `docker compose run --rm backend uv run pytest tests/test_api.py -q -k recent`
  Expected: FAIL (404 on `/api/trips/recent`).
- [ ] **Step 3: Add the columns** to `schema.sql`:
  `ALTER TABLE trips ADD COLUMN IF NOT EXISTS resolved_destination TEXT, ADD COLUMN IF NOT EXISTS destination_lat DOUBLE PRECISION, ADD COLUMN IF NOT EXISTS destination_lng DOUBLE PRECISION;`
  Add a one-line comment on why: "the typed destination often differs from where the planner ends".
- [ ] **Step 4: Implement `resolve_trip` and `recent_trips` in `UsageRepository`.**
  - `RECENT_TRIPS_LIMIT = 8`.
  - The SQL uses `DISTINCT ON (lower(origin), lower(destination))` over the routed, non-team rows, then orders the outer query by `created_at DESC` and applies `LIMIT`.
- [ ] **Step 5: Wire the route in `create_trip`'s `stream()`.**
  - On a `TripStarted` event, remember `event.hops[-1].destination`.
  - On a `TripMapped` event, find the point whose `name` equals that destination and, if found, `await services.usage.resolve_trip(trip_id, point.name, point.lat, point.lng)`.
  - Add `@router.get("/trips/recent")` returning `await _services(request).usage.recent_trips()`.
- [ ] **Step 6: Run the whole backend suite and confirm it passes.**
  Run: `docker compose run --rm backend uv run pytest -q`
  Expected: all pass.
- [ ] **Step 7: Mutation check, written into the commit body.**
  Drop `AND resolved_destination IS NOT NULL` from the SQL, confirm `test_recent_skips_trips_whose_last_stop_was_not_located` goes red, then revert.
- [ ] **Step 8: Commit.**
  `✨ feat(backend): record each trip's resolved destination and list recent searches`

### Task 2: Web foundations — tokens, Inter, type scale, logo, no motifs

**Files:**
- Modify: `web/styles/tokens.css`, `web/styles/app.css`, `web/app/landing.module.css`, `web/app/layout.tsx`, `web/components/Logo.tsx`, `web/components/ModeIcon.tsx`, `web/lib/format.ts` (`modeIconSrc`)
- Create: `web/app/fonts/Inter-latin.woff2`, `web/app/fonts/OFL-Inter.txt`, `web/app/icon.svg`, `web/public/modes/{bus,avion,tren,colectivo,combi,mototaxi,lancha}.svg`
- Delete: `web/components/Franja.tsx`, `web/public/textil/`, the three old font files and their OFL texts

**Interfaces:**
- Produces:
  - CSS variables `--acc`, `--acc-soft`, `--ink`, `--mute`, `--line`, `--soft`, `--font-inter`;
  - `<Logo inverted?: boolean />` (white wordmark for use over photos);
  - `modeIconSrc(mode)` → `/modes/<file>.svg`.

- [ ] **Step 1: Fetch Inter.**
  `curl -L -o web/app/fonts/Inter-latin.woff2 https://cdn.jsdelivr.net/npm/@fontsource-variable/inter@5.1.0/files/inter-latin-wght-normal.woff2`, plus the OFL text from the same package.
  Load it in `layout.tsx` as one `localFont` with `weight: "100 900"` and `variable: "--font-inter"`. Remove `Franja` from `layout.tsx`.
- [ ] **Step 2: Replace `tokens.css`** with the Global Constraints palette.
  In `app.css` and `landing.module.css`, rename the old variables:

  | Old | New |
  |---|---|
  | `--cochinilla`, `--cochinilla-purpura` | `--acc` |
  | `--lana` | `#fff` (via `--bg`) |
  | `--lana-oscura` | `--ink` |
  | `--hilo` | `--line` |
  | `--texto-secundario` | `--mute` |
  | `--input-bg` | `--soft` |
  | `--anil` | `--ink`, except live and progress, which become `--acc` |
  | `--qolle*`, `--chillka` | removed with their mode-tone rules |

  Every `font-family` becomes `var(--font-inter), system-ui, sans-serif`.
- [ ] **Step 3: Normalize every `font-size`** to 40/18/14. Rule of thumb: values ≥ 26 → 40, 16–22 → 18, ≤ 15 → 14. The mobile hero title is 32.
  Run: `grep -RnoE 'font-size: *[0-9.]+px' web/styles web/app | grep -vE ': *(40|18|14|32)px'`
  Expected: empty output.
- [ ] **Step 4: Logo.**
  - Inline SVG: a 26×26 rounded square `rx=8` filled `--acc`, with path `M7 17c3-8 9-8 12-3` (white, stroke 2.6, round cap) and a white circle at `cx=19 cy=14 r=2.2`.
  - Wordmark "ya sale", 18px, weight 800.
  - Write the same mark to `web/app/icon.svg`.
- [ ] **Step 5: Mode icons.** Monochrome line SVGs (stroke `#111114`, width 1.8, 24×24, no fill) for each file in `public/modes/`. Point `modeIconSrc` at them. Drop every `tone-*` and `bar-*` color rule.
- [ ] **Step 6: Verify.**
  - `cd web && pnpm exec tsc --noEmit && pnpm test && pnpm exec next build` passes.
  - `grep -RnE 'textil|Franja|cochinilla|qolle|chillka|anil|lana|bricolage|archivo|font-mono' web/app web/components web/styles web/lib` is empty.
- [ ] **Step 7: Commit.**
  `💄 style(web): carmine tokens, Inter in three sizes and an own logo`

### Task 3: Destination photo adapter (`web/lib/photos.ts`)

**Files:**
- Create: `web/lib/photos.ts`
- Test: `web/lib/photos.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface Photo { url: string; author: string; license: string; page: string }
  export function destinationPhoto(place: string, point: [number, number], fetcher?: typeof fetch, storage?: Pick<Storage, "getItem" | "setItem">): Promise<Photo | null>
  export function isPhotoFile(name: string): boolean          // false for /\.svg$|mapa|map|localizaci|location|escudo|bandera|flag|coat|logo/i
  export function plainText(html: string): string            // strips tags, decodes &amp; &quot; &#39; &lt; &gt;
  ```
  - `null` means "no photo found".
  - Network errors reject (fail loud). The caller shows the gradient and logs the error.

- [ ] **Step 1: Write the failing tests** with a fake `fetcher` that routes by URL:
  - `finds the photo by exact title when the article sits within 25 km`: "Kuélap" at (-6.42,-77.92), article at (-6.42,-77.95) with `Arquitectura_de_Kuelap.jpg`. Expect `url` to be the Commons `thumburl` (1280), `author: "Elemaki"`, `license: "CC BY-SA 2.5"`. Assert the first request URL contains `titles=Ku%C3%A9lap`.
  - `rejects a same-name article far away and tries "<name> (Perú)"`: "Sauce" with the article at (40.4,-3.7), then "Sauce (Perú)" at (-6.69,-76.22). Expect the second article's image.
  - `falls back to the nearest geosearch page whose image is a photo`: the title has no coordinates; the geosearch pages are `Peru_physical_map.svg` (index 1) and `Laguna.jpg` (index 2). Expect `Laguna.jpg`.
  - `returns null when nothing nearby has a photo`.
  - `isPhotoFile` table: `Kuelap.jpg` → true; `Mapa_de_localización_Puno.svg`, `Escudo_de_Ica.png`, `Bandera.jpg` → false.
  - `plainText('<a href="x">Elemaki</a> &amp; co')` → `"Elemaki & co"`.
  - `serves a cached photo without fetching and survives a storage that throws`: the second call with the same point makes 0 fetches. A storage whose `getItem`/`setItem` throw still returns the photo.
- [ ] **Step 2: Run the tests and confirm they fail.**
  Run: `cd web && pnpm exec vitest run lib/photos.test.ts`
  Expected: FAIL (module missing).
- [ ] **Step 3: Implement it.**
  - Endpoints and params exactly as in the spec: es.wikipedia `action=query&format=json&origin=*`; title step `prop=pageimages|coordinates&piprop=name&redirects=1`; geosearch `generator=geosearch&ggsradius=10000&ggslimit=20&prop=pageimages&piprop=name`, sorted by `index`; Commons `prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=1280`.
  - Build URLs with `URLSearchParams`.
  - Distance: equirectangular, as in `geophoto2.py` (`111 * hypot(dlat, dlng * cos(lat))`).
  - Cache key: `photo:${lat.toFixed(3)},${lng.toFixed(3)}`, kept in memory and in `storage` (each storage access inside `try/catch`). Default storage: `globalThis.localStorage`.
  - Commons `Artist` goes through `plainText`. If it is empty, use `"Wikimedia Commons"`.
- [ ] **Step 4: Run the tests and confirm they pass.**
  Run: `cd web && pnpm test`
  Expected: all pass.
- [ ] **Step 5: Commit.**
  `✨ feat(web): find a credited photo of each destination on Wikipedia`

### Task 4: `DestinationHero` component

**Files:**
- Create: `web/components/DestinationHero.tsx`
- Modify: `web/styles/app.css` (hero rules)

**Interfaces:**
- Consumes: `destinationPhoto`, `Photo` (Task 3); `Logo inverted` (Task 2).
- Produces:
  `<DestinationHero place={string|null} point={[number,number]|null} height="home"|"trip" nav={ReactNode} children={ReactNode} />`
  - It renders the photo (or the gradient when `place`/`point` is null, the lookup returns null, or the lookup rejects), the dark overlay, the credit line ("Foto: {author} · {license} · Wikimedia Commons", linking to `page`), `nav` at the top and `children` anchored bottom-left.
  - Heights: `home` = 420px, `trip` = 260px; on mobile, 360 and 220.

- [ ] **Step 1: Implement it.**
  - Lookup in a `useEffect` keyed on `place` and the point. A rejection calls `console.error("Destination photo lookup failed", error)` and shows the gradient.
  - The photo fades in (opacity 0→1, 600ms) when its `<img>` loads.
  - Ken Burns: `transform: scale(1.15)`→`scale(1)` over 16s, `ease-out`.
  - Gradient state: `linear-gradient(135deg, #C8102E, #111114)`.
  - Reduced motion: no zoom and no fade.
  - The `<img>` uses `alt=""`, and `referrerPolicy="no-referrer"` (Wikimedia hotlinking).
- [ ] **Step 2: Verify.**
  Run: `cd web && pnpm exec tsc --noEmit`
  The visual check comes in Tasks 5 and 6.
- [ ] **Step 3: Commit.**
  `✨ feat(web): add a destination hero with photo, credit and fallback`

### Task 5: Home page rebuilt

**Files:**
- Modify: `web/app/page.tsx`, `web/app/landing.module.css`, `web/components/landing/TripForm.tsx`, `web/lib/api.ts`, `web/lib/landing.ts` (if `tripHref` needs prefill support)
- Create: `web/components/landing/RecentSearches.tsx`
- Delete: `web/components/landing/RouteCards.tsx`, `SampleTrip.tsx`, `UsageProof.tsx`, `web/public/landing/`, and their tests and CSS
- Test: `web/lib/api.test.ts`

**Interfaces:**
- Consumes: `DestinationHero` (Task 4); `GET /api/trips/recent` (Task 1).
- Produces:
  - `export interface RecentTrip { origin: string; destination: string; place: string; at: string; lat: number; lng: number }`;
  - `export function fetchRecentTrips(): Promise<RecentTrip[]>`;
  - `parseRecentTrips(value: unknown): RecentTrip[]` (exported for tests, throws on a bad shape like the other parsers);
  - `TripForm` reads `o`, `d`, `f` from the URL query to prefill. Task 6's "Cambiar" links to `/?o=…&d=…&f=…#viaje`.

- [ ] **Step 1: Write the failing test** in `api.test.ts`:
  - `parseRecentTrips` accepts the Task 1 shape;
  - it throws `Invalid lat` when `lat` is a string.
- [ ] **Step 2: Run it and confirm it fails.**
  Run: `cd web && pnpm exec vitest run lib/api.test.ts`
  Expected: FAIL.
- [ ] **Step 3: Implement `parseRecentTrips` and `fetchRecentTrips`** with the existing `getJson` and `reqString`/`reqNumber` helpers.
- [ ] **Step 4: Rebuild `page.tsx`** per the spec's home sections, in order:
  1. `DestinationHero` (`height="home"`), fed by `recent[0]`, with the nav (Logo inverted · Comparar → `/comparar` · Uso real → `/uso` · Para agentes → `#agentes`), the pill "Última búsqueda: {origin} → {destination}, {relativeTime}" and the h1 "¿De dónde a dónde vas?" (40px), plus the 14px line "Cualquier punto del Perú, tramo por tramo, con precio, fuente y fecha.";
  2. the floating search card (`TripForm` restyled per `inicio.html`: Desde ⇄ Hasta · Cuándo · "Armar viaje");
  3. `RecentSearches`: title "Lo último que la gente buscó" (18px) and the note "Búsquedas reales · toca una para verla". It is a grid of 4 columns (2 on tablet, 1 on mobile). Each card has the photo via `destinationPhoto(place, [lat, lng])`, or the gradient; the title "{origin} → {destination}" with ellipsis on overflow; "hace N min" via the existing `relativeTime`. Each card links to `tripHref` for the trip with today's date. Hover lifts 3px with a shadow. The section is hidden when the list is empty;
  4. `<section id="agentes">` with `McpUrl` and one 14px sentence;
  5. a footer with a "Código en GitHub" link to `https://github.com/cuisangelo/ya-sale`.

  The `metadata` export stays.
- [ ] **Step 5: Verify.**
  - `cd web && pnpm exec tsc --noEmit && pnpm test` passes.
  - Playwright screenshots of `/` at 1280 and 390 px against the mock server (`$CLAUDE_JOB_DIR/tmp/harness/serve.py`, extended with a `GET /api/trips/recent` fixture of 6 trips) show: photo hero, floating search, 4-column recent grid, agents section and footer; no console errors.
- [ ] **Step 6: Commit.**
  `✨ feat(web): photo-first home with the latest real searches`

### Task 6: Trip view rebuilt

**Files:**
- Modify: `web/app/viaje/trip-screen.tsx`, `web/components/HopCard.tsx`, `web/components/LiveIndicator.tsx`, `web/components/TripSkeleton.tsx`, `web/components/TripMap.tsx` (colors only), `web/styles/app.css`, `web/lib/format.ts`
- Test: `web/lib/format.test.ts`

**Interfaces:**
- Consumes: `DestinationHero` (Task 4); `state.departures` keyed by `departuresKey(index, mode)` in `api.ts`.
- Produces: `firstDeparture(state: TripState, firstMode: Mode | undefined): { time: string; operator: string } | null` in `format.ts`. It returns the earliest `departs_at` of hop 0 with `firstMode`, formatted `HH:MM` in America/Lima.

- [ ] **Step 1: Write the failing tests** in `format.test.ts`:
  - `firstDeparture picks the earliest of hop 0`: departures at 21:00 and 12:00 on hop 0 → `{ time: "12:00", operator: … }`;
  - `firstDeparture ignores later hops`: hop 0 has none, hop 1 has 06:00 → `null`;
  - `firstDeparture returns null for an unknown mode`.
- [ ] **Step 2: Run them and confirm they fail.**
  Run: `cd web && pnpm exec vitest run lib/format.test.ts`
  Expected: FAIL.
- [ ] **Step 3: Implement `firstDeparture`**, using `Intl.DateTimeFormat("es-PE", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/Lima" })`.
- [ ] **Step 4: Rebuild the screen** per `viaje.html`:
  - **Hero:** `DestinationHero` (`height="trip"`) with `place = state.hops.at(-1)?.destination ?? destination`. The point is the `state.points` entry with that name, or null until `trip_mapped` arrives. The nav holds Logo inverted and the pill "{origin} → {destination} · {date} · Cambiar", linking to `/?o&d&f#viaje`. The title block is "Tu viaje a" (14) over the destination (40).
  - **Floating summary card**, overlapping the hero by 34px:
    - "Desde" holds `totals.price` in `--acc`, 18px;
    - "En camino" holds `totals.duration`;
    - "Tramos" holds "{n} · {n-1} transbordo(s)" ("directo" when 1);
    - "Primera salida" holds "{time} · {operator}" and is shown only when `firstDeparture` is non-null;
    - the restyled `LiveIndicator` sits on the right with a carmine dot and track.
  - **Body:** a two-column grid (legs 1.2fr, sticky map 1fr; one column under 860px).
    - `HopCard`: black square number badge; title 18px; neutral pill tabs (selected = ink background, white text; each shows "desde S/x"); departures as rows on `--soft` (logo, "Operador · HH:MM", origin/duration line in `--mute`, price 18px, carmine "Comprar" button); sources in `--mute`; the "Ver N opciones más" link in `--acc`.
    - Transfer: a dashed left border with "Transbordo en {place}" in `--mute`, no icons.
    - Loading: a carmine ring spinner replaces the chakana mask in `LoadingWords`; the skeletons stay.
  - **`TripMap`:** `TONE_COLORS` = land `#C8102E`, rail `#111114`, air `#111114` (dashed), water `#111114` (dashed). Markers are ink circles with a white border, with the origin in carmine.
  - **Animations:** the summary card rises with a fade over 400ms, and the legs rise over 500ms staggered by index (`animation-delay: calc(var(--i) * 120ms)`).
- [ ] **Step 5: Verify.**
  - `cd web && pnpm exec tsc --noEmit && pnpm test` passes.
  - The Playwright harness (`shoot.py` plus `shoot2.py`, extended with a `leg_departures` event) captures each phase at 1280 and 390 px with no console errors.
  - The font-size grep from Task 2 is still empty.
- [ ] **Step 6: Commit.**
  `✨ feat(web): photo-first trip view with the useful numbers on top`

### Task 7: Inherited pages, share image, ship

**Files:**
- Modify: `web/app/comparar/page.tsx`, `web/app/uso/page.tsx` (only class or markup fixes the token change forces), `BITACORA.md`
- Replace: `web/public/og-image.png` (1200×630)

- [ ] **Step 1: Check the two inherited pages.** Open `/comparar` and `/uso` in the harness at 1280 and 390 px, and fix only what the token change broke: contrast, removed classes.
- [ ] **Step 2: Rebuild the share image.** Render `og-image.png` from a throwaway HTML: carmine-to-ink gradient, white logo, "¿De dónde a dónde vas?" at 40px-equivalent scale, "yasale.cuisangelo.com". Take a Playwright screenshot at 1200×630 into `web/public/og-image.png`. The HTML stays in `$CLAUDE_JOB_DIR/tmp`.
- [ ] **Step 3: Run the full acceptance from the spec.**
  - backend pytest, web tsc, web test, and the font-size grep;
  - `pnpm exec next build`.
- [ ] **Step 4: Commit, push and open the PR.**
  - Commit `💄 style(web): carry the new identity to compare, usage and the share image`.
  - `git fetch && git rebase origin/main`, push the branch, `gh pr create`. The PR opens last, per verification §6.
- [ ] **Step 5: After the merge, verify live.**
  - Vercel status `success` for the merge SHA, and the backend CD run green;
  - `curl -s https://yasale.cuisangelo.com/api/trips/recent` → 200 JSON list;
  - the live `/` and `/viaje` chunks contain "Lo último que la gente buscó" and "Primera salida";
  - log a `Deploy` entry in `BITACORA.md`.
