import type { LegStatus } from "../lib/api";

const LABELS: Record<LegStatus, string> = {
  extracted: "Extraído",
  disputed: "En disputa",
  confirmed: "Confirmado",
};

export function StatusBadge({ status }: { status: LegStatus }) {
  return (
    <span className={`badge badge-${status}`}>
      {LABELS[status]}
    </span>
  );
}
