type Props = { items: { name: string; color: string }[] };

export function Legend({ items }: Props) {
  return (
    <ul className="legend">
      {items.map((i) => (
        <li key={i.name}>
          <span
            className="legend__swatch"
            style={{ background: i.color }}
            aria-hidden="true"
          />
          {i.name}
        </li>
      ))}
    </ul>
  );
}
