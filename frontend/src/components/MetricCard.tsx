type MetricCardProps = {
  accent: "teal" | "amber" | "rose" | "blue";
  detail: string;
  icon: string;
  label: string;
  value: string;
};

export function MetricCard({ accent, detail, icon, label, value }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${accent}`}>
      <span className="metric-card__icon" aria-hidden="true">
        {icon}
      </span>
      <div className="metric-card__content">
        <p className="metric-card__label">{label}</p>
        <strong className="metric-card__value">{value}</strong>
        <p className="metric-card__detail">{detail}</p>
      </div>
    </article>
  );
}
