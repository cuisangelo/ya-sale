import type { LegStatus } from "../lib/api";

const LABELS: Record<LegStatus, string> = {
  extracted: "Extraído",
  disputed: "En disputa",
  confirmed: "Confirmado",
};

export function StatusBadge({ status }: { status: LegStatus }) {
  return (
    <span className={`badge badge-${status}`}>
      {status === "confirmed" ? (
        <img src="/textil/motivo-chaska.svg" alt="" width={12} height={12} />
      ) : null}
      {LABELS[status]}
    </span>
  );
}
