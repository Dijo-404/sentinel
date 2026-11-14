import type { PortalRole } from "../../../tests/stubs/identity";
import { previewPermissions } from "@/lib/permissions";

type Props = {
  role: Exclude<PortalRole, "customer">;
};

/** Advisory only — does not grant or enforce permissions. */
export function PermissionPreview({ role }: Props) {
  const items = previewPermissions(role);
  return (
    <div
      className="panel stack"
      data-testid="permission-preview"
      data-role={role}
    >
      <h2>Permission preview</h2>
      <p className="muted">
        Advisory summary for reviewers. Authorization is enforced server-side.
      </p>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
