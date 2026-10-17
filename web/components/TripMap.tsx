"use client";

import "leaflet/dist/leaflet.css";
import type { LatLngTuple, Map as LeafletMap, Polyline } from "leaflet";
import { useEffect, useRef, useState } from "react";
import type { Hop, MapPoint, Mode } from "../lib/api";
import { modeTone, type ModeTone } from "../lib/format";
import { roadPath } from "../lib/roads";

const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · rutas <a href="https://project-osrm.org">OSRM</a>';
const DRAW_MS = 900;

const TONE_COLORS: Record<ModeTone, string> = {
  land: "#C8102E",
  air: "#111114",
  rail: "#111114",
  water: "#111114",
};

// Straight water legs are approximate, so they read as dashed like a flight, never as a road.
const DASHES: Record<ModeTone, string | undefined> = {
  land: undefined,
  air: "2 9",
  rail: undefined,
  water: "8 8",
};

interface TripMapProps {
  hops: Hop[];
  points: MapPoint[];
  selected: Mode[];
  active: number | null;
}

interface Segment {
  index: number;
  tone: ModeTone;
  ends: [LatLngTuple, LatLngTuple];
  // Null while a land leg waits for its road geometry.
  path: LatLngTuple[] | null;
}

export function TripMap({ hops, points, selected, active }: TripMapProps) {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<LeafletMap | null>(null);
  const lines = useRef<Map<number, Polyline>>(new Map());
  const drawn = useRef(new Set<string>());
  const [roads, setRoads] = useState<Record<string, LatLngTuple[]>>({});
  const [approximate, setApproximate] = useState(false);
  const segments = buildSegments(hops, points, selected, roads);
  const ready = segments.filter((segment): segment is Segment & { path: LatLngTuple[] } => segment.path !== null);
  const waiting = segments.filter((segment) => segment.path === null);
  const signature = JSON.stringify(ready.map((s) => [s.index, s.tone, s.path.length, s.path[0], s.path.at(-1)]));
  const waitingSignature = JSON.stringify(waiting.map((s) => s.ends));

  useEffect(() => {
    let cancelled = false;
    for (const { ends } of waiting) {
      const [[fromLat, fromLng], [toLat, toLng]] = ends;
      void roadPath([fromLat, fromLng], [toLat, toLng])
        .catch((error: unknown) => {
          // A missing road must not hide the leg: draw it straight and say so on the map.
          console.error("Road route failed, drawing a straight line", error);
          if (!cancelled) setApproximate(true);
          return ends;
        })
        .then((path) => {
          if (!cancelled) setRoads((current) => ({ ...current, [roadKey(ends)]: path }));
        });
    }
    return () => {
      cancelled = true;
    };
    // waitingSignature captures the pairs still missing a road; the array itself is new each render.
  }, [waitingSignature]);

  useEffect(() => {
    if (!host.current || ready.length === 0) return;
    let cancelled = false;
    void import("leaflet").then((L) => {
      if (cancelled || !host.current) return;
      if (!map.current) {
        map.current = L.map(host.current, { zoomControl: false, attributionControl: true, scrollWheelZoom: false });
        L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 18 }).addTo(map.current);
        L.control.zoom({ position: "bottomright" }).addTo(map.current);
      }
      const leaflet = map.current;
      lines.current.forEach((line) => line.remove());
      lines.current.clear();
      leaflet.eachLayer((layer) => {
        if (layer instanceof L.Marker) layer.remove();
      });

      const motion = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      let order = 0;
      for (const segment of ready) {
        const key = JSON.stringify([segment.index, segment.tone, segment.path.length]);
        const animate = motion && !drawn.current.has(key);
        drawn.current.add(key);
        const line = L.polyline(animate ? [segment.path[0]] : segment.path, {
          color: TONE_COLORS[segment.tone],
          weight: 4,
          opacity: 0.9,
          dashArray: DASHES[segment.tone],
          lineCap: "round",
        }).addTo(leaflet);
        lines.current.set(segment.index, line);
        if (animate) drawAlong(line, segment.path, order++ * DRAW_MS);
      }
      for (const point of points) {
        L.marker([point.lat, point.lng], {
          icon: L.divIcon({ className: "map-stop", html: "<span></span>", iconSize: [16, 16] }),
          keyboard: false,
        })
          .bindTooltip(point.name, { permanent: true, direction: "right", offset: [8, 0], className: "map-label" })
          .addTo(leaflet);
      }
      leaflet.fitBounds(L.latLngBounds(ready.flatMap((s) => s.path)), { padding: [36, 36] });
    });
    return () => {
      cancelled = true;
    };
    // The signature captures every input that changes what is drawn; the arrays themselves are new each render.
  }, [signature]);

  useEffect(() => {
    const leaflet = map.current;
    lines.current.forEach((line, index) => line.setStyle({ weight: index === active ? 7 : 4 }));
    const line = active == null ? undefined : lines.current.get(active);
    if (leaflet && line) leaflet.flyToBounds(line.getBounds(), { padding: [48, 48], duration: 0.8, maxZoom: 11 });
  }, [active]);

  useEffect(
    () => () => {
      map.current?.remove();
      map.current = null;
    },
    [],
  );

  return (
    <div className="trip-map-frame">
      <div ref={host} className="trip-map" role="img" aria-label="Mapa de la ruta del viaje" />
      {ready.length === 0 ? (
        <p className="trip-map-empty">
          {segments.length === 0 ? "Ubicando los lugares del viaje…" : "Trazando las rutas por carretera…"}
        </p>
      ) : null}
      {approximate ? <p className="trip-map-note">Sin ruta por carretera: trazo aproximado</p> : null}
    </div>
  );
}

function buildSegments(
  hops: Hop[],
  points: MapPoint[],
  selected: Mode[],
  roads: Record<string, LatLngTuple[]>,
): Segment[] {
  const byName = new Map(points.map((point) => [point.name, [point.lat, point.lng] as LatLngTuple]));
  const segments: Segment[] = [];
  hops.forEach((hop, index) => {
    const from = byName.get(hop.origin);
    const to = byName.get(hop.destination);
    if (!from || !to) return;
    const tone = modeTone(selected[index] ?? hop.modes[0]);
    const ends: [LatLngTuple, LatLngTuple] = [from, to];
    // Only land legs follow roads; rivers and rail lines share nothing with a car route.
    const path = tone === "air" ? arc(from, to) : tone === "land" ? (roads[roadKey(ends)] ?? null) : ends;
    segments.push({ index, tone, ends, path });
  });
  return segments;
}

function roadKey([from, to]: [LatLngTuple, LatLngTuple]): string {
  return `${from.join(",")};${to.join(",")}`;
}

// A flight reads as a flight when it bows away from the road below it.
function arc(from: LatLngTuple, to: LatLngTuple, steps = 32): LatLngTuple[] {
  const [lat1, lng1] = from;
  const [lat2, lng2] = to;
  const bow = 0.2;
  const controlLat = (lat1 + lat2) / 2 + (lng2 - lng1) * bow;
  const controlLng = (lng1 + lng2) / 2 - (lat2 - lat1) * bow;
  return Array.from({ length: steps + 1 }, (_, i) => {
    const t = i / steps;
    const u = 1 - t;
    return [u * u * lat1 + 2 * u * t * controlLat + t * t * lat2, u * u * lng1 + 2 * u * t * controlLng + t * t * lng2];
  });
}

function drawAlong(line: Polyline, path: LatLngTuple[], delay: number) {
  const dense = path.length > 2 ? path : straight(path[0], path[1]);
  const started = performance.now() + delay;
  const step = (now: number) => {
    const progress = Math.min(1, Math.max(0, (now - started) / DRAW_MS));
    const eased = 1 - (1 - progress) ** 3;
    const count = Math.max(1, Math.round(eased * (dense.length - 1)));
    line.setLatLngs(dense.slice(0, count + 1));
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function straight(from: LatLngTuple, to: LatLngTuple, steps = 32): LatLngTuple[] {
  return Array.from({ length: steps + 1 }, (_, i) => {
    const t = i / steps;
    return [from[0] + (to[0] - from[0]) * t, from[1] + (to[1] - from[1]) * t];
  });
}
