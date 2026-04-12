interface StatCardProps {
  readonly label: string;
  readonly value: string;
  readonly description: string;
}

export function StatCard({
  label,
  value,
  description,
}: StatCardProps): JSX.Element {
  return (
    <article className="stat-card">
      <span className="stat-card__label">{label}</span>
      <strong className="stat-card__value">{value}</strong>
      <p className="stat-card__description">{description}</p>
    </article>
  );
}
