"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { limaToday, tripHref } from "../../lib/landing";
import styles from "../../app/landing.module.css";

export function TripForm() {
  const router = useRouter();
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");
  const [today, setToday] = useState("");
  const [error, setError] = useState<string | null>(null);

  // The page is a static export, so today's date and the "Cambiar" prefill must be read in the browser.
  useEffect(() => {
    const now = limaToday(new Date());
    const query = new URLSearchParams(window.location.search);
    setToday(now);
    setOrigin(query.get("o") ?? "");
    setDestination(query.get("d") ?? "");
    setDate(query.get("f") ?? now);
  }, []);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = tripHref({ origin, destination, date }, limaToday(new Date()));
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setError(null);
    router.push(result.href);
  }

  function swap() {
    setOrigin(destination);
    setDestination(origin);
  }

  return (
    <form className={styles.search} action="/viaje/" method="get" onSubmit={onSubmit} noValidate>
      <label className={`${styles.searchField} ${styles.from}`}>
        Desde
        <input
          id="origen"
          name="o"
          value={origin}
          onChange={(event) => setOrigin(event.target.value)}
          placeholder="Lima"
          autoComplete="off"
          required
        />
      </label>
      <button className={styles.swap} type="button" onClick={swap} aria-label="Intercambiar origen y destino">
        ⇄
      </button>
      <label className={`${styles.searchField} ${styles.to}`}>
        Hasta
        <input
          name="d"
          value={destination}
          onChange={(event) => setDestination(event.target.value)}
          placeholder="Kuélap, Máncora, Uros…"
          autoComplete="off"
          required
        />
      </label>
      <label className={`${styles.searchField} ${styles.when}`}>
        Cuándo
        <input
          name="f"
          type="date"
          value={date}
          min={today || undefined}
          onChange={(event) => setDate(event.target.value)}
          required
        />
      </label>
      <button className={styles.go} type="submit">
        Armar viaje
      </button>
      {error ? (
        <p className={styles.formError} role="alert">
          {error}
        </p>
      ) : null}
    </form>
  );
}
