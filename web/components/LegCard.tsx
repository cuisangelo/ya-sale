import type { LegSlot } from "../lib/api";
import { freshnessLine, legFactParts, modeLabel, modeTone, purchaseUrl } from "../lib/format";
import { ModeIcon } from "./ModeIcon";
import { StatusBadge } from "./StatusBadge";

export function LegCard({ slot, now }: { slot: LegSlot; now: number }) {
  const summary = slot.summary;
  if (!summary) {
    return (
      <article className="leg-card bar-land">
        <div className="leg-body">
          <strong>Tramo {slot.index + 1}</strong>
          {slot.error ? <p className="leg-error">{slot.error}</p> : null}
        </div>
      </article>
    );
  }

  const facts = legFactParts(summary.version);
  const buy = purchaseUrl(summary.version.purchase_url);
  const pending = !slot.live && !slot.error;

  return (
    <article className={`leg-card bar-${modeTone(summary.mode)}${pending ? " is-pending" : ""}`}>
      <ModeIcon mode={summary.mode} />
      <div className="leg-body">
        <strong>
          {modeLabel(summary.mode)} · {summary.origin} → {summary.destination}
        </strong>
        {facts.length > 0 || buy ? (
          <div className="leg-facts">
            {facts.join(" · ")}
            {facts.length > 0 && buy ? " · " : null}
            {buy ? (
              <a href={buy} target="_blank" rel="noreferrer">
                comprar en el sitio
              </a>
            ) : null}
          </div>
        ) : null}
        <div className="mono source">{freshnessLine(slot, now)}</div>
        {slot.error ? <p className="leg-error">{slot.error}</p> : null}
      </div>
      <StatusBadge status={summary.status} />
    </article>
  );
}
