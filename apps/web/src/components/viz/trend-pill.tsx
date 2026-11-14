type Props = {
  value: string;
  direction: "up" | "down" | "flat";
  /** Colour by meaning, not direction: fewer exceptions is good. Defaults to up = good. */
  tone?: "good" | "bad" | "neutral";
};

const PATH: Record<Props["direction"], string> = {
  up: "M3 9l3-3 3 3",
  down: "M3 3l3 3 3-3",
  flat: "M2 6h8",
};

export function TrendPill({ value, direction, tone }: Props) {
  const resolved =
    tone ??
    (direction === "up" ? "good" : direction === "down" ? "bad" : "neutral");
  return (
    <span
      className="trend-pill"
      data-direction={direction}
      data-tone={resolved}
      data-testid="trend-pill"
    >
      <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
        <path
          d={PATH[direction]}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {value}
    </span>
  );
}
