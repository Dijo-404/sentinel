import { switchWorkspaceAction } from "@/lib/server/auth-actions";
import type { PortalRole } from "../../../tests/stubs/identity";

export type WorkspaceOption = {
  assignment_id: string;
  role: PortalRole;
  label: string;
};

type Props = {
  workspaces: WorkspaceOption[];
  activeAssignmentId?: string;
  /** Compact list for sidebar; default is full unauthorized-style list. */
  compact?: boolean;
};

export function WorkspaceSwitcher({ workspaces, activeAssignmentId, compact = false }: Props) {
  const others = compact
    ? workspaces.filter((w) => w.assignment_id !== activeAssignmentId)
    : workspaces;
  if (others.length === 0) return null;

  return (
    <ul
      data-testid="workspace-switcher"
      className={compact ? "app-sidebar__workspaces" : undefined}
    >
      {others.map((w) => (
        <li key={w.assignment_id}>
          <form action={switchWorkspaceAction}>
            <input type="hidden" name="assignment_id" value={w.assignment_id} />
            <button
              type="submit"
              className={compact ? "btn btn-glass" : "btn"}
              data-testid={`switch-workspace-${w.role}`}
            >
              {compact ? w.role : w.label}
            </button>
          </form>
        </li>
      ))}
    </ul>
  );
}
