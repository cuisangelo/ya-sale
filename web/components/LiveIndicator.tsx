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
  return (
    <p className={live ? "live live-on" : "live"} aria-live="polite">
      <span className="live-dot" aria-hidden="true" />
      {text}
    </p>
  );
}
