import { switchWorkspaceAction } from "@/lib/server/auth-actions";
import type { PortalRole } from "../../../tests/stubs/identity";

export type WorkspacePickerOption = {
  assignment_id: string;
  role: PortalRole;
  label: string;
};

type Props = {
  workspaces: WorkspacePickerOption[];
  activeAssignmentId?: string;
  error?: { code: string; message: string } | null;
};

export function WorkspacePicker({ workspaces, activeAssignmentId, error }: Props) {
  if (error) {
    return (
      <div className="auth-card panel stack" data-testid="auth-workspaces">
        <p className="brand auth-brand">Sentinel</p>
        <h1>Choose workspace</h1>
        <div className="state-banner" data-tone="error" data-testid="peer-error" role="alert">
          <strong>Identity unavailable</strong>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            {error.message}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-card panel stack" data-testid="auth-workspaces">
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>Choose workspace</h1>
        <p className="muted">Select an assignment for this session.</p>
      </div>

      {workspaces.length === 0 ? (
        <div className="state-banner" data-tone="empty" data-testid="state-empty" role="status">
          <strong>No workspaces</strong>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            This account has no assignments.
          </p>
        </div>
      ) : (
        <ul data-testid="auth-workspaces-list" className="stack">
          {workspaces.map((w) => {
            const active = w.assignment_id === activeAssignmentId;
            return (
              <li key={w.assignment_id}>
                <form action={switchWorkspaceAction}>
                  <input type="hidden" name="assignment_id" value={w.assignment_id} />
                  <button
                    type="submit"
                    className="btn"
                    disabled={active}
                    data-testid={`select-workspace-${w.assignment_id}`}
                  >
                    {active ? `${w.label} (active)` : w.label}
                  </button>
                </form>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
