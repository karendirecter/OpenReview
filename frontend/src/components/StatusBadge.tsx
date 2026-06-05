import { formatStatusLabel } from "../lib/format";

type StatusBadgeProps = {
  status: string;
};

function getStatusTone(status: string) {
  const normalized = status.toLowerCase();

  if (/(success|complete|completed|done|resolved|passed)/.test(normalized)) {
    return "success";
  }

  if (/(running|queued|progress|pending|processing)/.test(normalized)) {
    return "info";
  }

  if (/(warning|partial|retry)/.test(normalized)) {
    return "warning";
  }

  if (/(error|failed|failure|cancelled|canceled)/.test(normalized)) {
    return "danger";
  }

  return "neutral";
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const tone = getStatusTone(status);

  return <span className={`status-badge status-badge--${tone}`}>{formatStatusLabel(status)}</span>;
}
