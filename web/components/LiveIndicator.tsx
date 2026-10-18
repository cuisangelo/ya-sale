export function LiveIndicator({
  current,
  planned,
  live,
}: {
  current: number;
  planned: number;
  live: boolean;
}) {
  const text = live
    ? `Actualizando en vivo · ${current} de ${planned} tramos`
    : `Listo · ${current} de ${planned} tramos`;
  // A sliver stays visible at 0 so the bar reads as started, not empty.
  const filled = live ? Math.max(current / planned, 0.06) : 1;
  return (
    <div className={live ? "live-box" : "live-box is-done"}>
      <p className={live ? "live live-on" : "live"} aria-live="polite">
        <span className="live-dot" aria-hidden="true" />
        {text}
      </p>
      <span
        className="live-bar"
        role="progressbar"
        aria-label="Tramos actualizados"
        aria-valuemin={0}
        aria-valuemax={planned}
        aria-valuenow={current}
      >
        <span className="live-fill" style={{ width: `${filled * 100}%` }} />
      </span>
    </div>
  );
}
