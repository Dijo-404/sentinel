import type { ReactNode } from "react";

type Props = {
  title: string;
  children: ReactNode;
};

export function ChartCard({ title, children }: Props) {
  return (
    <section className="chart-card" data-testid="chart-card">
      <h3 className="chart-card__title">{title}</h3>
      {children}
    </section>
  );
}
