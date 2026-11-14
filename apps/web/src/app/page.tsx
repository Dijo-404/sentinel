import Link from "next/link";

const PORTALS = [
  { href: "/customer/login", label: "Customer" },
  { href: "/merchant/login", label: "Merchant" },
  { href: "/operator/login", label: "Support Operator" },
  { href: "/supervisor/login", label: "Supervisor" },
  { href: "/risk/login", label: "Risk & Fraud" },
  { href: "/admin/login", label: "Platform Admin" },
] as const;

export default function HomePage() {
  return (
    <div className="auth-page">
      <div className="auth-card panel stack" data-testid="portal-entry">
        <p className="brand auth-brand">Sentinel</p>
        <h1>Role portals</h1>
        <p className="muted">
          Choose a workspace login. Roles are resolved server-side — login URLs
          do not grant access.
        </p>
        <p className="fixture-banner" role="status">
          Fixture identity stub — synthetic demo users only
        </p>
        <nav className="portal-grid" aria-label="Portal entry">
          {PORTALS.map((p) => (
            <Link key={p.href} className="portal-link" href={p.href}>
              {p.label}
            </Link>
          ))}
        </nav>
        <p className="muted">
          Legacy routes kept for compatibility:{" "}
          <Link href="/intake">/intake</Link> · <Link href="/ops">/ops</Link>
        </p>
      </div>
    </div>
  );
}
