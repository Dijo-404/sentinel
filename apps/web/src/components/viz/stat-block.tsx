type Props = {
  label: string;
  value: string;
  caption?: string;
};

export function StatBlock({ label, value, caption }: Props) {
  return (
    <article className="stat-block" data-testid="stat-block">
      <p className="stat-block__label">{label}</p>
      <p className="stat-block__value">{value}</p>
      {caption ? <p className="stat-block__caption">{caption}</p> : null}
    </article>
  );
}
