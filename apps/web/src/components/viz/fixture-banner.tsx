const SIMULATOR_COPY = "Simulator / fixture — not live production metrics";

export function FixtureBanner() {
  return (
    <div className="fixture-banner" role="status" data-testid="fixture-banner">
      <span className="fixture-banner__dot" aria-hidden="true" />
      <span>{SIMULATOR_COPY}</span>
    </div>
  );
}
