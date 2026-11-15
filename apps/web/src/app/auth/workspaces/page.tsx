import { AuthShell } from "@/components/auth/auth-shell";
import Link from "next/link";
import { WorkspacePicker } from "@/components/auth/workspace-picker";
import { PeerError } from "@/domain/types";
import { readSessionId, workspaceChoices } from "@/lib/server/auth";
import { getIdentityClient } from "@/lib/server/identity-client";

export default async function AuthWorkspacesPage() {
  const sessionId = await readSessionId();
  if (!sessionId) {
    return (
      <AuthShell>
        <div className="auth-card panel stack" data-testid="auth-workspaces">
          <p className="brand auth-brand">Sentinel</p>
          <h1>Choose workspace</h1>
          <p className="muted">Sign in to list your workspaces.</p>
          <p>
            <Link href="/login">Sign in</Link>
          </p>
        </div>
      </AuthShell>
    );
  }

  try {
    const listed = await getIdentityClient().listWorkspaces(sessionId);
    const workspaces = workspaceChoices(listed.workspaces);
    return (
      <AuthShell>
        <WorkspacePicker
          workspaces={workspaces}
          activeAssignmentId={listed.active_assignment?.assignment_id}
        />
      </AuthShell>
    );
  } catch (err) {
    const message = err instanceof PeerError ? err.message : "Identity peer unavailable";
    return (
      <AuthShell>
        <WorkspacePicker
          workspaces={[]}
          error={{
            code: err instanceof PeerError ? err.code : "PEER_UNAVAILABLE",
            message,
          }}
        />
      </AuthShell>
    );
  }
}
