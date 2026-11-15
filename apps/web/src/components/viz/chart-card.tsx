import type { ReactNode } from "react";

type Props = {
  title: string;
  /** One line explaining how to read the chart. */
  subtitle?: string;
  /** Right-aligned header slot (legend, toggle). */
  aside?: ReactNode;
  className?: string;
  /** Distinct test id when a page shows more than one card. */
  testId?: string;
  children: ReactNode;
};

export function ChartCard({
  title,
  subtitle,
  aside,
  className,
  testId = "chart-card",
  children,
}: Props) {
  return (
    <section className={`chart-card${className ? ` ${className}` : ""}`} data-testid={testId}>
      <header className="chart-card__head">
        <div>
          <h3 className="chart-card__title">{title}</h3>
          {subtitle ? <p className="chart-card__subtitle">{subtitle}</p> : null}
        </div>
        {aside}
      </header>
      {children}
    </section>
  );
}
