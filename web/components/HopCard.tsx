import type { Hop, LegSlot, Mode, Option, Version } from "../lib/api";
import {
  formatDuration,
  formatPrice,
  freshnessLine,
  mapsDirectionsUrl,
  modeLabel,
  modeTone,
  priceFloor,
  purchaseUrl,
  sourceLabel,
} from "../lib/format";
import { ModeIcon } from "./ModeIcon";
import { StatusBadge } from "./StatusBadge";

interface HopCardProps {
  index: number;
  hop: Hop;
  slots: Partial<Record<Mode, LegSlot>>;
  selected: Mode;
  active: boolean;
  now: number;
  onSelect: (mode: Mode) => void;
  onFocus: () => void;
}

export function HopCard({ index, hop, slots, selected, active, now, onSelect, onFocus }: HopCardProps) {
  const slot = slots[selected];
  const summary = slot?.summary ?? null;
  const pending = !slot?.live && !slot?.error;

  return (
    <article
      className={`hop-card bar-${modeTone(selected)}${active ? " is-active" : ""}${pending ? " is-pending" : ""}`}
      onPointerEnter={onFocus}
      onFocus={onFocus}
    >
      <header className="hop-head">
        <span className="hop-step" aria-hidden="true">
          <span>{index + 1}</span>
        </span>
        <h2 className="hop-route">
          {hop.origin} → {hop.destination}
        </h2>
        {summary ? <StatusBadge status={summary.status} /> : null}
      </header>

      {hop.modes.length > 1 ? (
        <div className="mode-tabs" role="tablist" aria-label={`Cómo ir de ${hop.origin} a ${hop.destination}`}>
          {hop.modes.map((mode) => {
            const tab = slots[mode];
            const floor = tab?.summary ? priceFloor(tab.summary.version, tab.options) : null;
            return (
              <button
                key={mode}
                type="button"
                role="tab"
                aria-selected={mode === selected}
                className={`mode-tab tab-${modeTone(mode)}`}
                onClick={() => onSelect(mode)}
              >
                <ModeIcon mode={mode} />
                <span className="mode-tab-text">
                  <strong>{modeLabel(mode)}</strong>
                  <span>{floor ?? (tab?.error ? "sin datos" : "buscando…")}</span>
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="mode-single">
          <ModeIcon mode={selected} />
          <strong>{modeLabel(selected)}</strong>
        </div>
      )}

      {slot && summary ? (
        <LegDetails slot={slot} version={summary.version} town={hop.origin} now={now} />
      ) : (
        <p className={slot?.error ? "leg-error" : "loading"}>
          {slot?.error ?? `Buscando ${modeLabel(selected).toLowerCase()} de ${hop.origin} a ${hop.destination}…`}
        </p>
      )}
    </article>
  );
}

function LegDetails({ slot, version, town, now }: { slot: LegSlot; version: Version; town: string; now: number }) {
  const price = formatPrice(version.price_min_pen, version.price_max_pen);
  const buy = purchaseUrl(version.purchase_url);
  const note = [version.operator, version.schedule_note].filter(Boolean).join(". ");

  return (
    <div className="hop-details">
      <dl className="hop-figures">
        <div>
          <dt>Pasaje</dt>
          <dd>{price ?? "sin precio publicado"}</dd>
        </div>
        <div>
          <dt>Viaje</dt>
          <dd>{version.duration_min != null ? formatDuration(version.duration_min) : "sin dato"}</dd>
        </div>
      </dl>

      {version.departure_point ? (
        <p className="hop-departure">
          <span>
            Sale de <strong>{version.departure_point}</strong>
          </span>
          <a
            className="maps-link"
            href={mapsDirectionsUrl(version.departure_point, town)}
            target="_blank"
            rel="noreferrer"
          >
            <img src="/textil/motivo-chakana.svg" alt="" width={14} height={14} />
            Cómo llegar
          </a>
        </p>
      ) : null}
      {note ? <p className="hop-note">{note}</p> : null}
      {buy ? (
        <a className="buy-link" href={buy} target="_blank" rel="noreferrer">
          Comprar en el sitio de quien vende
        </a>
      ) : null}
      <p className="mono source">{freshnessLine(slot, now)}</p>
      {slot.error ? <p className="leg-error">{slot.error}</p> : null}

      {slot.options.length > 1 ? <OptionList options={slot.options} /> : null}
    </div>
  );
}

function OptionList({ options }: { options: Option[] }) {
  return (
    <details className="options">
      <summary>Ver las {options.length} opciones que encontramos</summary>
      <ul>
        {options.map((option, position) => (
          <li key={`${option.source_url}-${position}`} className="option-row">
            <div className="option-what">
              <strong>{option.operator ?? "Sin empresa indicada"}</strong>
              {option.schedule_note ? <span>{option.schedule_note}</span> : null}
              {option.departure_point ? <span>Sale de {option.departure_point}</span> : null}
            </div>
            <div className="option-figures">
              <strong>{formatPrice(option.price_min_pen, option.price_max_pen) ?? "sin precio"}</strong>
              {option.duration_min != null ? <span>{formatDuration(option.duration_min)}</span> : null}
            </div>
            <a className="option-source mono" href={option.source_url} target="_blank" rel="noreferrer">
              {sourceLabel(option.source_url)}
            </a>
          </li>
        ))}
      </ul>
    </details>
  );
}
