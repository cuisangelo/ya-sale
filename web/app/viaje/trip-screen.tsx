"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Fragment, useEffect, useState } from "react";
import { LegCard } from "../../components/LegCard";
import { LiveIndicator } from "../../components/LiveIndicator";
import { Logo } from "../../components/Logo";
import {
  confirmLeg,
  correctLeg,
  errorText,
  initialTripState,
  isAbortError,
  reduceTrip,
  streamTrip,
  type CorrectionInput,
  type TripState,
} from "../../lib/api";
import { itineraryMeta, modeLabel } from "../../lib/format";

const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function TripScreen() {
  const searchParams = useSearchParams();
  const origin = (searchParams.get("o") ?? "").trim();
  const destination = (searchParams.get("d") ?? "").trim();
  const date = (searchParams.get("f") ?? "").trim();
  const ready = origin !== "" && destination !== "" && DATE.test(date);

  const [state, setState] = useState<TripState>(initialTripState);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [displayName, setDisplayName] = useState("");
  const [correcting, setCorrecting] = useState(false);
  const [selectedLeg, setSelectedLeg] = useState("");
  const [departurePoint, setDeparturePoint] = useState("");
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [duration, setDuration] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setStreamError(null);
    setState(initialTripState);
    if (!ready) return;
    let ignore = false;
    const handle = streamTrip({ origin, destination, date }, (event) => {
      if (ignore) return;
      setState((current) => reduceTrip(current, event));
    });
    void handle.finished.catch((error: unknown) => {
      if (ignore || isAbortError(error)) return;
      setStreamError(errorText(error, "No se pudo armar el viaje."));
    });
    return () => {
      ignore = true;
      handle.abort();
    };
  }, [ready, origin, destination, date]);

  useEffect(() => {
    if (!state.legs.some((leg) => leg.live)) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [state.legs]);

  if (!ready) {
    return (
      <main className="shell shell-narrow">
        <Logo size={36} compact />
        <p className="banner">Indica origen, destino y fecha de salida.</p>
        <Link href="/">Volver al inicio</Link>
      </main>
    );
  }

  const meta = itineraryMeta(state.legs, state.legsPlanned, state.done);
  const legsWithSummary = state.legs.filter((leg) => leg.summary);
  const selected = selectedLeg || (legsWithSummary[0] ? String(legsWithSummary[0].summary?.leg_id) : "");

  async function confirmRoute() {
    setActionError(null);
    setNotice(null);
    if (legsWithSummary.length === 0) {
      setActionError("Todavía no hay tramos para confirmar.");
      return;
    }
    const name = displayName.trim() || null;
    setBusy(true);
    const failures: string[] = [];
    try {
      for (const slot of legsWithSummary) {
        const summary = slot.summary;
        if (!summary) continue;
        try {
          const updated = await confirmLeg(summary.leg_id, summary.version.id, name);
          setState((current) =>
            reduceTrip(current, { event: "leg_refreshed", data: { index: slot.index, ...updated } }),
          );
        } catch (error) {
          failures.push(error instanceof Error ? error.message : "No se pudo confirmar.");
        }
      }
    } finally {
      setBusy(false);
    }
    if (failures.length > 0) setActionError(failures.join(" "));
    else setNotice("Ruta confirmada.");
  }

  async function submitCorrection(event: FormEvent) {
    event.preventDefault();
    setActionError(null);
    setNotice(null);
    const legId = Number(selected);
    const slot = state.legs.find((leg) => leg.summary?.leg_id === legId);
    if (!slot?.summary) {
      setActionError("Elige el tramo que quieres corregir.");
      return;
    }
    let input: CorrectionInput;
    try {
      input = correctionInput({
        departurePoint,
        priceMin,
        priceMax,
        duration,
        displayName,
      });
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Revisa la corrección.");
      return;
    }
    if (!input) return;
    setBusy(true);
    try {
      const updated = await correctLeg(slot.summary.leg_id, input);
      setState((current) =>
        reduceTrip(current, { event: "leg_refreshed", data: { index: slot.index, ...updated } }),
      );
      setNotice("Corrección guardada.");
      setCorrecting(false);
      setDeparturePoint("");
      setPriceMin("");
      setPriceMax("");
      setDuration("");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "No se pudo guardar la corrección.");
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    const url = window.location.href;
    const text = `${origin} → ${destination}`;
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title: "Ya Sale", text, url });
        return;
      } catch (error) {
        if (isAbortError(error)) return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setActionError(url);
    }
  }

  return (
    <main className="shell shell-narrow">
      <Logo size={36} compact />
      <div className="itinerary-head">
        <div>
          <div className="eyebrow">Tu viaje</div>
          <h1 className="trip-title">
            {origin} → {destination}
          </h1>
          {meta ? <div className="mono meta">{meta}</div> : null}
        </div>
        {state.legsPlanned > 0 && !state.noRouteMessage ? (
          <LiveIndicator current={state.progress.done} planned={state.progress.planned} live={!state.done} />
        ) : null}
      </div>

      {state.noRouteMessage ? <p className="banner">{state.noRouteMessage}</p> : null}
      {streamError ? <p className="banner">{streamError}</p> : null}
      {!state.noRouteMessage && state.legsPlanned === 0 && !streamError ? (
        <p className="loading">Armando tu viaje…</p>
      ) : null}

      {state.legs.map((slot, position) => {
        const previous = position > 0 ? state.legs[position - 1] : null;
        const modeChanged = Boolean(
          previous?.summary && slot.summary && previous.summary.mode !== slot.summary.mode,
        );
        return (
          <Fragment key={slot.index}>
            {previous ? (
              <div className="join">
                <span className="mayu" aria-hidden="true" />
                {modeChanged && previous.summary ? (
                  <>
                    <img src="/textil/motivo-chakana.svg" alt="" width={18} height={18} />
                    <span>Transbordo en {previous.summary.destination}</span>
                  </>
                ) : null}
              </div>
            ) : null}
            <LegCard slot={slot} now={now} />
          </Fragment>
        );
      })}

      {state.legs.length > 0 ? (
        <div className="actions">
          <label className="field field-name">
            Tu nombre (opcional)
            <input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Ana"
              maxLength={80}
            />
          </label>
          <button className="btn btn-primary" type="button" disabled={busy} onClick={() => void confirmRoute()}>
            ¿Hiciste esta ruta? Confírmala
          </button>
          <button
            className="btn btn-secondary"
            type="button"
            disabled={busy || legsWithSummary.length === 0}
            aria-expanded={correcting}
            onClick={() => setCorrecting((open) => !open)}
          >
            Corregir un tramo
          </button>
          <button className="btn btn-ghost" type="button" onClick={() => void share()}>
            {copied ? "Enlace copiado" : "Compartir"}
          </button>
        </div>
      ) : null}

      {correcting ? (
        <form className="correct-form" onSubmit={(event) => void submitCorrection(event)}>
          <label className="field wide">
            Tramo
            <select value={selected} onChange={(event) => setSelectedLeg(event.target.value)}>
              {legsWithSummary.map((slot) =>
                slot.summary ? (
                  <option key={slot.summary.leg_id} value={slot.summary.leg_id}>
                    {modeLabel(slot.summary.mode)} · {slot.summary.origin} → {slot.summary.destination}
                  </option>
                ) : null,
              )}
            </select>
          </label>
          <label className="field">
            Paradero de salida
            <input value={departurePoint} onChange={(event) => setDeparturePoint(event.target.value)} />
          </label>
          <label className="field">
            Duración (minutos)
            <input inputMode="numeric" value={duration} onChange={(event) => setDuration(event.target.value)} />
          </label>
          <label className="field">
            Precio mínimo (S/)
            <input inputMode="decimal" value={priceMin} onChange={(event) => setPriceMin(event.target.value)} />
          </label>
          <label className="field">
            Precio máximo (S/)
            <input inputMode="decimal" value={priceMax} onChange={(event) => setPriceMax(event.target.value)} />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            Guardar corrección
          </button>
        </form>
      ) : null}

      {actionError ? <p className="banner">{actionError}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}
    </main>
  );
}

function correctionInput(values: {
  departurePoint: string;
  priceMin: string;
  priceMax: string;
  duration: string;
  displayName: string;
}): CorrectionInput {
  const input: CorrectionInput = {};
  const departure = values.departurePoint.trim();
  if (departure) input.departure_point = departure;
  const min = readMoney(values.priceMin, "precio mínimo");
  const max = readMoney(values.priceMax, "precio máximo");
  if (min) input.price_min_pen = min;
  if (max) input.price_max_pen = max;
  const minutes = values.duration.trim();
  if (minutes) {
    if (!/^\d+$/.test(minutes)) throw new Error("La duración va en minutos enteros.");
    input.duration_min = Number(minutes);
  }
  const name = values.displayName.trim();
  if (name) input.display_name = name;
  if (
    input.departure_point == null &&
    input.price_min_pen == null &&
    input.price_max_pen == null &&
    input.duration_min == null
  ) {
    throw new Error("Escribe el dato que quieres corregir.");
  }
  return input;
}

function readMoney(value: string, label: string): string | undefined {
  const trimmed = value.trim().replace(",", ".");
  if (!trimmed) return undefined;
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) {
    throw new Error(`El ${label} va en soles, por ejemplo 12.50.`);
  }
  return trimmed;
}
