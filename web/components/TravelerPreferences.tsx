"use client";

import { FormEvent, useEffect, useState } from "react";
import { routeAdvice, preferenceLabels } from "../lib/advice";
import {
  clearPreferences,
  errorText,
  fetchPreferences,
  savePreferences,
  type Mode,
  type PreferencesState,
  type Schedule,
  type TripState,
} from "../lib/api";

interface Props {
  trip: TripState;
  selectedModes: Mode[];
}

export function TravelerPreferences({ trip, selectedModes }: Props) {
  const [saved, setSaved] = useState<PreferencesState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [cheapest, setCheapest] = useState(false);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    fetchPreferences()
      .then((state) => {
        if (!ignore) setSaved(state);
      })
      .catch((reason: unknown) => {
        if (!ignore) setLoadError(errorText(reason, "No pudimos leer tus preferencias guardadas. Tu viaje se muestra igual."));
      });
    return () => {
      ignore = true;
    };
  }, []);

  if (loadError) return <p className="notice prefs-status">{loadError}</p>;
  // Without the feature, or before it answers, the trip page stays exactly as it was.
  if (!saved?.enabled) return null;

  const preferences = saved.preferences;

  function startEditing() {
    setSchedule(preferences?.schedule ?? null);
    setCheapest(preferences?.cheapest ?? false);
    setConsent(false);
    setError(null);
    setNotice(null);
    setEditing(true);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      setSaved(await savePreferences({ schedule, cheapest }));
      setEditing(false);
      setConsent(false);
      setNotice("Preferencias guardadas.");
    } catch (reason) {
      setError(errorText(reason, "No se guardaron tus preferencias."));
    } finally {
      setBusy(false);
    }
  }

  async function forget() {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      setSaved(await clearPreferences());
      setEditing(false);
      setSchedule(null);
      setCheapest(false);
      setConsent(false);
      setNotice("Borramos tus preferencias.");
    } catch (reason) {
      setError(errorText(reason, "No se pudieron borrar tus preferencias."));
    } finally {
      setBusy(false);
    }
  }

  const feedback = (
    <>
      {error ? <p className="banner prefs-status">{error}</p> : null}
      {notice ? <p className="notice prefs-status">{notice}</p> : null}
    </>
  );

  if (!preferences || editing) {
    const chosen = schedule !== null || cheapest;
    return (
      <section className="prefs" aria-labelledby="prefs-title">
        <h2 id="prefs-title" className="prefs-title">
          {preferences ? "Cambia tus preferencias" : "¿Cómo te gusta viajar?"}
        </h2>
        <p className="prefs-lead">Guárdalo una vez y en cada viaje te señalamos la salida que te conviene.</p>
        <form className="prefs-form" onSubmit={(event) => void submit(event)}>
          <fieldset className="prefs-choices">
            <legend>Horario</legend>
            {([null, "day", "night"] as const).map((value) => (
              <label key={value ?? "any"} className="prefs-choice">
                <input type="radio" name="schedule" checked={schedule === value} onChange={() => setSchedule(value)} />
                {value === null ? "Me da igual" : value === "day" ? "De día" : "De noche"}
              </label>
            ))}
          </fieldset>
          <label className="prefs-choice">
            <input type="checkbox" checked={cheapest} onChange={(event) => setCheapest(event.target.checked)} />
            Busco el precio más bajo
          </label>
          <label className="prefs-consent">
            <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
            Acepto que Ya Sale guarde estas preferencias en Atomic Memory, ligadas a una cookie anónima de este
            navegador. No necesitas cuenta y puedes borrarlas cuando quieras.
          </label>
          <div className="prefs-actions">
            <button className="btn btn-primary" type="submit" disabled={busy || !consent || !chosen}>
              Guardar preferencias
            </button>
            {preferences ? (
              <button className="btn btn-ghost" type="button" disabled={busy} onClick={() => setEditing(false)}>
                Cancelar
              </button>
            ) : null}
          </div>
        </form>
        {feedback}
      </section>
    );
  }

  const advice = routeAdvice(trip, selectedModes, preferences);
  return (
    <section className="prefs" aria-labelledby="prefs-title">
      <div className="prefs-head">
        <h2 id="prefs-title" className="prefs-title">
          Consejos para ti
        </h2>
        <ul className="prefs-tags" aria-label="Tus preferencias guardadas">
          {preferenceLabels(preferences).map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      </div>
      {advice.length > 0 ? (
        <ul className="prefs-advice">
          {advice.map((item) => (
            <li key={`${item.hop}-${item.title}`}>
              <span className="prefs-advice-hop">{item.hop}</span>
              <strong>{item.title}</strong>
              <span>
                {item.link ? (
                  <a href={item.link} target="_blank" rel="noopener noreferrer">
                    {item.detail}
                  </a>
                ) : (
                  item.detail
                )}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="prefs-lead">
          {trip.done
            ? "Este viaje no tiene salidas con horario o precio para aplicar tus preferencias."
            : "Buscando salidas que encajen con tus preferencias…"}
        </p>
      )}
      <div className="prefs-actions">
        <button className="btn btn-secondary" type="button" disabled={busy} onClick={startEditing}>
          Cambiar
        </button>
        <button className="btn btn-ghost" type="button" disabled={busy} onClick={() => void forget()}>
          Borrar mis preferencias
        </button>
      </div>
      {feedback}
    </section>
  );
}
