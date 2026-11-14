const SIMULATOR_COPY =
  "Simulator / fixture — not live production metrics";

export function FixtureBanner() {
  return (
    <div
      className="fixture-banner"
      role="status"
      data-testid="fixture-banner"
    >
      <strong>Simulator</strong>
      <span>{SIMULATOR_COPY}</span>
    </div>
  );
}
