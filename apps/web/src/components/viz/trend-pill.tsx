type Props = {
  value: string;
  direction: "up" | "down" | "flat";
};

const ARROW: Record<Props["direction"], string> = {
  up: "↑",
  down: "↓",
  flat: "→",
};

export function TrendPill({ value, direction }: Props) {
  return (
    <span
      className="trend-pill"
      data-direction={direction}
      data-testid="trend-pill"
    >
      <span aria-hidden="true">{ARROW[direction]}</span>
      {value}
    </span>
  );
}
