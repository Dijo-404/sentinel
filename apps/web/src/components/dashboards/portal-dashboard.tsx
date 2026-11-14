import type { PortalRole } from "../../../tests/stubs/identity";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";

type Props = {
  role: PortalRole;
  session: AuthSession;
  highlights?: string[];
};

export function PortalDashboard({ role, session, highlights }: Props) {
  const meta = PORTAL_META[role];
  const items = highlights ?? [
    "Fixture-mode scaffold — domain peers not assembled",
    `Signed in as ${session.user.email}`,
    `Active assignment: ${session.assignment.label}`,
  ];

  return (
    <div className="stack" data-testid={`${role}-dashboard`}>
      <div className="panel stack">
        <h1>{meta.title} dashboard</h1>
        <p className="muted">{meta.description}</p>
        <p className="fixture-banner" role="status">
          Simulator / fixture data — not live production metrics
        </p>
      </div>
      <div className="panel">
        <h2>Overview</h2>
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
