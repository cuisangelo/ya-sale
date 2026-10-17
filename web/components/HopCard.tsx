import { type CSSProperties, type ReactNode, useState } from "react";
import type { Departure, Hop, LegSlot, Mode, Option, Version } from "../lib/api";
import {
  datedLink,
  departureClock,
  departuresHeading,
  formatDuration,
  formatPrice,
  freshnessLine,
  initials,
  logoDomain,
  logoSrc,
  mapsDirectionsUrl,
  modeLabel,
  optionLink,
  priceFloor,
  purchaseUrl,
  seatsLabel,
  sourceLabel,
  type TripDay,
} from "../lib/format";
import { LoadingWords } from "./LoadingWords";
import { ModeIcon } from "./ModeIcon";
import { StatusBadge } from "./StatusBadge";

interface HopCardProps {
  index: number;
  hop: Hop;
  slots: Partial<Record<Mode, LegSlot>>;
  selected: Mode;
  departures: Departure[];
  date: string;
  active: boolean;
  now: number;
  onSelect: (mode: Mode) => void;
  onFocus: () => void;
}

export function HopCard({ index, hop, slots, selected, departures, date, active, now, onSelect, onFocus }: HopCardProps) {
  const slot = slots[selected];
  const summary = slot?.summary ?? null;
  const pending = !slot?.live && !slot?.error;

  return (
    <article
      className={`hop-card${active ? " is-active" : ""}${pending ? " is-pending" : ""}`}
      // The index staggers each card's entrance in CSS.
      style={{ "--i": index } as CSSProperties}
      onPointerEnter={onFocus}
      onFocus={onFocus}
    >
      <header className="hop-head">
        <span className="hop-step" aria-hidden="true">
          {index + 1}
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
                className="mode-tab"
                onClick={() => onSelect(mode)}
              >
                <ModeIcon mode={mode} />
                {modeLabel(mode)}
                <small className={floor || tab?.error ? undefined : "tab-searching"}>
                  {floor ?? (tab?.error ? "sin datos" : "buscando…")}
                </small>
              </button>
            );
          })}
        </div>
      ) : (
        <p className="mode-single">
          <ModeIcon mode={selected} />
          {modeLabel(selected)}
        </p>
      )}

      {slot && summary ? (
        <LegDetails
          slot={slot}
          version={summary.version}
          trip={{ origin: hop.origin, destination: hop.destination, date }}
          now={now}
        >
          <DepartureList departures={departures} date={date} />
        </LegDetails>
      ) : (
        <>
          {slot?.error ? <p className="leg-error">{slot.error}</p> : <PendingLeg mode={selected} hop={hop} />}
          <DepartureList departures={departures} date={date} />
        </>
      )}
    </article>
  );
}

function PendingLeg({ mode, hop }: { mode: Mode; hop: Hop }) {
  return (
    <div className="hop-pending">
      <div className="skeleton-figures" aria-hidden="true">
        <span className="skeleton-block" />
        <span className="skeleton-block" />
      </div>
      <LoadingWords
        words={[
          `Buscando ${modeLabel(mode).toLowerCase()} de ${hop.origin} a ${hop.destination}…`,
          "Leyendo páginas de empresas y viajeros…",
          "Anotando precios, horarios y paraderos…",
          "Comparando lo que dice cada fuente…",
        ]}
      />
    </div>
  );
}

interface LegDetailsProps {
  slot: LegSlot;
  version: Version;
  trip: TripDay;
  now: number;
  children: ReactNode;
}

function LegDetails({ slot, version, trip, now, children }: LegDetailsProps) {
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
            href={mapsDirectionsUrl(version.departure_point, trip.origin)}
            target="_blank"
            rel="noreferrer"
          >
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

      {children}
      {slot.options.length > 1 ? <OptionList options={slot.options} trip={trip} /> : null}
    </div>
  );
}

// Each row opens that exact departure on the seller's site, where the seat is picked.
function DepartureList({ departures, date }: { departures: Departure[]; date: string }) {
  if (departures.length === 0) return null;
  const heading = departuresHeading(date);
  return (
    <section className="departures" aria-label={heading}>
      <h3>{heading}</h3>
      <ul>
        {departures.map((departure, position) => {
          const facts = [
            departure.arrives_at ? `llega ${departureClock(departure.arrives_at)}` : null,
            seatsLabel(departure.seats_available),
            sourceLabel(departure.booking_url),
          ].filter(Boolean);
          return (
            // A seller without per-departure pages links every departure of the day to the same list.
            <li key={`${departure.booking_url}-${position}`}>
              <a className="dep-row" href={departure.booking_url} target="_blank" rel="noreferrer">
                <OptionLogo operator={departure.operator} link={departure.booking_url} />
                <span className="dep-what">
                  <strong>
                    {departure.operator} · {departureClock(departure.departs_at)}
                  </strong>
                  <small>{facts.join(" · ")}</small>
                </span>
                <span className="dep-price">{formatPrice(departure.price_pen, null) ?? "sin precio"}</span>
                <span className="dep-buy">Comprar</span>
              </a>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function OptionList({ options, trip }: { options: Option[]; trip: TripDay }) {
  return (
    <details className="options">
      <summary>Ver las {options.length} opciones que encontramos</summary>
      <ul>
        {options.map((option, position) => {
          const link = datedLink(optionLink(option), trip);
          const content = (
            <>
              <OptionLogo operator={option.operator} link={link} />
              <div className="option-what">
                <strong>{option.operator ?? "Sin empresa indicada"}</strong>
                {option.schedule_note ? <span>{option.schedule_note}</span> : null}
                {option.departure_point ? <span>Sale de {option.departure_point}</span> : null}
              </div>
              <div className="option-figures">
                <strong>{formatPrice(option.price_min_pen, option.price_max_pen) ?? "sin precio"}</strong>
                {option.duration_min != null ? <span>{formatDuration(option.duration_min)}</span> : null}
              </div>
              <span className="option-source mono">
                {link && sourceLabel(link) !== sourceLabel(option.source_url)
                  ? `${sourceLabel(link)} · dato de ${sourceLabel(option.source_url)}`
                  : sourceLabel(option.source_url)}
              </span>
            </>
          );
          return (
            <li key={`${option.source_url}-${position}`}>
              {link ? (
                <a className="option-row" href={link} target="_blank" rel="noreferrer">
                  {content}
                </a>
              ) : (
                <div className="option-row">{content}</div>
              )}
            </li>
          );
        })}
      </ul>
    </details>
  );
}

function OptionLogo({ operator, link }: { operator: string | null; link: string | null }) {
  const domain = logoDomain(link);
  const [missing, setMissing] = useState(false);
  const label = operator ?? domain ?? "?";
  return (
    <span className="option-logo" aria-hidden="true">
      {domain && !missing ? (
        <img src={logoSrc(domain)} alt="" width={28} height={28} onError={() => setMissing(true)} />
      ) : (
        initials(label)
      )}
    </span>
  );
}
