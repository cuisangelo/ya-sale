"use client";

import type { LegSummary } from "../../lib/api";
import { formatDate, legFactParts, modeLabel, modeTone, summarySourceLine } from "../../lib/format";
import { ModeIcon } from "../ModeIcon";
import { StatusBadge } from "../StatusBadge";
import styles from "../../app/landing.module.css";
import { useOpenTrip } from "./useOpenTrip";

// Copied from production (GET /api/legs/3 and /api/legs/1). The visitor sees a real answer before
// searching, and a static copy costs no search credits on every landing visit. Only the place names
// were capitalized and the bus schedule note shortened; every value and source is as stored.
const LEGS: LegSummary[] = [
  {
    leg_id: 3,
    mode: "bus",
    origin: "Cusco",
    destination: "Ollantaytambo",
    status: "extracted",
    version: {
      id: 2,
      departure_point: null,
      operator: null,
      price_min_pen: "35.0",
      price_max_pen: null,
      duration_min: 113,
      schedule_note: "Primera partida 03:00, última 20:00; 148 servicios diarios",
      purchase_url: "https://www.redbus.pe/pasajes-de-bus/cusco-a-ollantaytambo",
      source_url: "https://www.redbus.pe/pasajes-de-bus/cusco-a-ollantaytambo",
      fetched_at: "2026-10-17T20:33:37.202567+00:00",
      confirmations: 0,
    },
  },
  {
    leg_id: 1,
    mode: "tren",
    origin: "Ollantaytambo",
    destination: "Aguas Calientes",
    status: "extracted",
    version: {
      id: 12,
      departure_point: "Ollantaytambo",
      operator: "Tren Local (Perú Rail)",
      price_min_pen: "15.0",
      price_max_pen: "15.0",
      duration_min: null,
      schedule_note: "Salidas 05:07, 9:49, 12:58, 19:00, 21:00. Compra personal con DNI.",
      purchase_url: null,
      source_url: "https://www.machupicchumagico.com/horarios-tren-local-machu-picchu",
      fetched_at: "2026-10-17T20:33:26.496838+00:00",
      confirmations: 0,
    },
  },
];

export function SampleTrip({ className }: { className: string }) {
  const openTrip = useOpenTrip();

  return (
    <aside className={`${className} ${styles.sample}`} aria-labelledby="muestra-titulo">
      <p className="eyebrow">Así responde Ya Sale · un viaje real</p>
      <h2 id="muestra-titulo" className="trip-title">
        Cusco → Aguas Calientes
      </h2>
      <p className="mono meta">
        {LEGS.length} tramos · consultado el {formatDate(LEGS[0].version.fetched_at)}
      </p>
      {LEGS.map((leg, index) => (
        <div key={leg.leg_id}>
          {index > 0 ? (
            <div className="join">
              <span className="join-line" aria-hidden="true" />
              Transbordo en {leg.origin}
            </div>
          ) : null}
          <article className={`leg-card bar-${modeTone(leg.mode)}`}>
            <ModeIcon mode={leg.mode} />
            <div className="leg-body">
              <strong>
                {modeLabel(leg.mode)} · {leg.origin} → {leg.destination}
              </strong>
              <div className="leg-facts">{legFactParts(leg.version).join(" · ")}</div>
              <div className="mono source">{summarySourceLine(leg)}</div>
            </div>
            <StatusBadge status={leg.status} />
          </article>
        </div>
      ))}
      <button type="button" className={`btn btn-secondary ${styles.sampleCta}`} onClick={() => openTrip("Cusco", "Aguas Calientes")}>
        Buscarlo en vivo ahora
      </button>
    </aside>
  );
}
