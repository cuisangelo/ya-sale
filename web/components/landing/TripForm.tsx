"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { limaToday, tripHref, type TripDraft } from "../../lib/landing";
import styles from "../../app/landing.module.css";

const EXAMPLES = [
  ["Cusco", "Aguas Calientes"],
  ["Iquitos", "Nauta"],
  ["Lima", "Sauce"],
  ["Arequipa", "Chivay"],
] as const;

export function TripForm() {
  const router = useRouter();
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");
  const [today, setToday] = useState("");
  const [error, setError] = useState<string | null>(null);

  // The page is a static export, so today's date must come from the visitor's clock, not the build.
  useEffect(() => {
    const now = limaToday(new Date());
    setToday(now);
    setDate(now);
  }, []);

  function go(draft: TripDraft) {
    const result = tripHref(draft, limaToday(new Date()));
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setError(null);
    router.push(result.href);
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    go({ origin, destination, date });
  }

  return (
    <>
      <form className={`trip-form ${styles.form}`} action="/viaje/" method="get" onSubmit={onSubmit} noValidate>
        <label className="field">
          Origen
          <input
            id="origen"
            name="o"
            value={origin}
            onChange={(event) => setOrigin(event.target.value)}
            placeholder="Lima, Miraflores"
            autoComplete="off"
            required
          />
        </label>
        <label className="field">
          Destino
          <input
            name="d"
            value={destination}
            onChange={(event) => setDestination(event.target.value)}
            placeholder="Sauce, San Martín"
            autoComplete="off"
            required
          />
        </label>
        <label className="field">
          Fecha de salida <span className="field-hint">(solo ida)</span>
          <input
            name="f"
            type="date"
            value={date}
            min={today || undefined}
            onChange={(event) => setDate(event.target.value)}
            required
          />
        </label>
        <button className="btn btn-primary" type="submit">
          Armar mi viaje
        </button>
        {error ? (
          <p className={`${styles.formError} wide`} role="alert">
            {error}
          </p>
        ) : null}
      </form>
      <div className="chips">
        <span>Prueba con:</span>
        {EXAMPLES.map(([from, to]) => (
          <button
            key={`${from}-${to}`}
            type="button"
            className="chip"
            onClick={() => {
              setOrigin(from);
              setDestination(to);
              go({ origin: from, destination: to, date });
            }}
          >
            {from} → {to}
          </button>
        ))}
      </div>
    </>
  );
}
