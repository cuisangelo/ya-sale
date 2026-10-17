"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Logo } from "../components/Logo";

const EXAMPLES = [
  ["Cusco", "Aguas Calientes"],
  ["Iquitos", "Nauta"],
  ["Lima", "Sauce"],
  ["Arequipa", "Chivay"],
] as const;

export default function HomePage() {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");

  return (
    <main className="shell">
      <Logo />
      <h1>¿De dónde a dónde vas?</h1>
      <p className="subtitle">
        Tu viaje a cualquier punto del Perú, tramo por tramo: bus, avión, tren, colectivo, combi,
        mototaxi o lancha. Con precios, paraderos y quién lo confirmó.
      </p>
      <form className="trip-form" action="/viaje/" method="get">
        <label className="field">
          Origen
          <input
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
          <input name="f" type="date" value={date} onChange={(event) => setDate(event.target.value)} required />
        </label>
        <button className="btn btn-primary" type="submit">
          Armar mi viaje
        </button>
      </form>
      <div className="chips">
        <span>Prueba:</span>
        {EXAMPLES.map(([from, to]) => (
          <button
            key={`${from}-${to}`}
            type="button"
            className="chip"
            aria-pressed={origin === from && destination === to}
            onClick={() => {
              setOrigin(from);
              setDestination(to);
            }}
          >
            {from} → {to}
          </button>
        ))}
      </div>
      <div className="footer-row">
        <span>
          <b>Úsalo desde ChatGPT o Claude:</b> conecta el MCP <McpUrl />
        </span>
        <Link href="/comparar/">Ver la comparación →</Link>
        <Link href="/uso/">Uso en vivo →</Link>
      </div>
    </main>
  );
}

function McpUrl() {
  const [href, setHref] = useState("/mcp");
  useEffect(() => {
    setHref(new URL("/mcp", window.location.origin).href);
  }, []);
  return (
    <a href={href}>
      <code>{href}</code>
    </a>
  );
}
