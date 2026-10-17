"use client";

import { useEffect, useState } from "react";
import { Logo } from "../../components/Logo";
import { errorText, fetchUsage, type Usage } from "../../lib/api";
import { formatCount, modeLabel, relativeTime } from "../../lib/format";

export default function UsagePage() {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    let ignore = false;
    fetchUsage().then(
      (next) => {
        if (ignore) return;
        setNow(Date.now());
        setUsage(next);
      },
      (caught: unknown) => {
        if (ignore) return;
        setError(errorText(caught, "No se pudo cargar el uso."));
      },
    );
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <main className="shell shell-wide">
      <Logo />
      <h1 className="trip-title">Así se está usando Ya Sale</h1>
      {error ? <p className="banner">{error}</p> : null}
      {!usage && !error ? <p className="loading">Cargando el uso en vivo…</p> : null}
      {usage ? (
        <>
          <div className="stats-grid">
            <Stat tone="land" value={usage.trips} label="viajes armados" />
            <Stat tone="air" value={usage.destinations} label="destinos distintos" />
            <Stat tone="water" value={usage.people} label="personas distintas" />
            <Stat tone="rail" value={usage.confirmed_legs} label="tramos confirmados" />
          </div>
          <section className="panel">
            <b>Últimas confirmaciones y correcciones</b>
            {usage.recent.length === 0 ? <p>Todavía no hay confirmaciones ni correcciones.</p> : null}
            {usage.recent.map((item, index) => (
              <div className="recent-row" key={`${item.at}-${item.origin}-${item.destination}-${index}`}>
                <span>
                  <b>{item.display_name ?? "Alguien"}</b>{" "}
                  {item.kind === "confirmation" ? "confirmó" : "corrigió"}{" "}
                  <b>
                    {modeLabel(item.mode)} · {item.origin} → {item.destination}
                  </b>
                </span>
                <span className="mono when">{relativeTime(item.at, now)}</span>
              </div>
            ))}
          </section>
          <p className="footnote">
            Datos reales de la base, sin cuentas del equipo ni tráfico automatizado. Personas distintas
            = huella anónima, sin datos personales.
          </p>
        </>
      ) : null}
    </main>
  );
}

function Stat({ tone, value, label }: { tone: "land" | "air" | "rail" | "water"; value: number; label: string }) {
  return (
    <article className={`stat bar-${tone}`}>
      <div className="stat-value">{formatCount(value)}</div>
      <div className="stat-label">{label}</div>
    </article>
  );
}
