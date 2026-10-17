"use client";

import { FormEvent, useState } from "react";
import { Logo } from "../../components/Logo";
import { StatusBadge } from "../../components/StatusBadge";
import { compareQuestion, errorText, type CompareResult } from "../../lib/api";
import { columnCounter, legFactParts, modeLabel, modeTone, summarySourceLine } from "../../lib/format";

export default function ComparePage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (!text) {
      setError("Escribe la pregunta que quieres comparar.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await compareQuestion(text));
    } catch (caught) {
      setResult(null);
      setError(errorText(caught, "No se pudo comparar."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell shell-wide">
      <Logo size={36} compact />
      <form className="question-card" onSubmit={(event) => void submit(event)}>
        <label className="field wide">
          Pregunta
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Quiero ir de Lima a Sauce sin tour, salgo el domingo. ¿Cómo llego y cuánto me cuesta?"
          />
        </label>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Comparando…" : "Comparar"}
        </button>
      </form>
      {error ? <p className="banner">{error}</p> : null}
      {result ? (
        <>
          <div className="compare-grid">
            <section className="column">
              <div className="compare-head">
                <b>Claude solo</b>
                <span className="mono meta">{columnCounter(result.plain.sources, result.plain.dated)}</span>
              </div>
              <p className="answer">{result.plain.text}</p>
            </section>
            <section className="column column-tools">
              <div className="compare-head">
                <span className="brand-mark">
                  <img src="/textil/logo-inti.svg" alt="" width={22} height={22} />
                  <b>Claude + Ya Sale</b>
                </span>
                <span className="mono meta">
                  {columnCounter(result.with_tools.sources, result.with_tools.dated)}
                </span>
              </div>
              {result.with_tools.text ? <p className="answer">{result.with_tools.text}</p> : null}
              <div className="compare-legs">
                {result.with_tools.legs.map((leg) => {
                  const facts = legFactParts(leg.version);
                  return (
                    <div key={leg.leg_id} className={`compare-leg bar-${modeTone(leg.mode)}`}>
                      <div className="compare-leg-head">
                        <strong>
                          {modeLabel(leg.mode)} · {leg.origin} → {leg.destination}
                        </strong>
                        <StatusBadge status={leg.status} />
                      </div>
                      {facts.length > 0 ? <div>{facts.join(" · ")}</div> : null}
                      <div className="mono source">{summarySourceLine(leg)}</div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
          <div className="counter-row">
            <span>
              Tramos con fuente: <span className="count-plain">{result.plain.sources}</span>
              {" vs "}
              <span className="count-tools">{result.with_tools.sources}</span>
            </span>
            <span>
              Datos con fecha: <span className="count-plain">{result.plain.dated}</span>
              {" vs "}
              <span className="count-tools">{result.with_tools.dated}</span>
            </span>
            <span>
              Confirmados por personas: <span className="count-plain">{result.plain.confirmed}</span>
              {" vs "}
              <span className="count-tools">{result.with_tools.confirmed}</span>
            </span>
          </div>
        </>
      ) : null}
    </main>
  );
}
