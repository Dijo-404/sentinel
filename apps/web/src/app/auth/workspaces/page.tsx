import Link from "next/link";
import { WorkspacePicker } from "@/components/auth/workspace-picker";
import { PeerError } from "@/domain/types";
import { getAuthSession, workspaceChoices } from "@/lib/server/auth";
import { getIdentityClient } from "@/lib/server/identity-client";

export default async function AuthWorkspacesPage() {
  const session = await getAuthSession();
  if (!session) {
    return (
      <div className="auth-page">
        <div className="auth-card panel stack" data-testid="auth-workspaces">
          <p className="brand auth-brand">Sentinel</p>
          <h1>Choose workspace</h1>
          <p className="muted">Sign in to list your workspaces.</p>
          <p>
            <Link href="/login">Sign in</Link>
          </p>
        </div>
      </div>
    );
  }

  try {
    const listed = await getIdentityClient().listWorkspaces(session.session.session_id);
    const workspaces = workspaceChoices(listed.workspaces);
    return (
      <div className="auth-page">
        <WorkspacePicker
          workspaces={workspaces}
          activeAssignmentId={
            listed.active_assignment?.assignment_id ?? session.assignment.assignment_id
          }
        />
      </div>
    );
  } catch (err) {
    const message = err instanceof PeerError ? err.message : "Identity peer unavailable";
    return (
      <div className="auth-page">
        <WorkspacePicker
          workspaces={[]}
          error={{
            code: err instanceof PeerError ? err.code : "PEER_UNAVAILABLE",
            message,
          }}
        />
      </div>
    );
  }
}
