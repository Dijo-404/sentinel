import { AuthShell } from "@/components/auth/auth-shell";
import Link from "next/link";
import { WorkspaceSwitcher } from "@/components/identity/workspace-switcher";
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
    <AuthShell>
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
            <p>Switch to an authorized workspace:</p>
            <WorkspaceSwitcher
              activeAssignmentId={session?.assignment.assignment_id}
              workspaces={workspaces}
            />
          </div>
        ) : (
          <p>
            <Link href="/">Return to portal entry</Link>
          </p>
        )}
      </div>
    </AuthShell>
  );
}
