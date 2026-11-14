import Link from "next/link";
import { getAuthSession, workspaceChoices } from "@/lib/server/auth";

export default async function UnauthorizedPage({
  searchParams,
}: {
  searchParams: Promise<{ portal?: string }>;
}) {
  const params = await searchParams;
  const session = await getAuthSession();
  const workspaces = session ? workspaceChoices(session.workspaces) : [];

  return (
    <div className="auth-page">
      <div className="auth-card panel stack" data-testid="unauthorized">
        <p className="brand auth-brand">Sentinel</p>
        <h1>Workspace not available</h1>
        <p className="muted">
          {params.portal
            ? `This account does not have the ${params.portal} workspace.`
            : "You are not authorized for this page."}
        </p>
        {workspaces.length > 0 ? (
          <div>
            <p>Your authorized workspaces:</p>
            <ul data-testid="authorized-workspaces">
              {workspaces.map((w) => (
                <li key={w.href}>
                  <Link href={w.href}>{w.label}</Link>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p>
            <Link href="/">Return to portal entry</Link>
          </p>
        )}
      </div>
    </div>
  );
}
