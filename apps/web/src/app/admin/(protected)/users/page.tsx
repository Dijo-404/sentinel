import Link from "next/link";
import { requireRole } from "@/lib/server/authorization";
import { getIdentityClient } from "@/lib/server/identity-client";

export default async function AdminUsersPage() {
  const session = await requireRole("admin");
  const identity = getIdentityClient();
  const staff = await identity.listStaffUsers(session.session.session_id);
  const invitations = await identity.listInvitations(session.session.session_id);

  if ("error" in staff || "error" in invitations) {
    return (
      <div className="state-banner" data-tone="permission" role="alert">
        Forbidden
      </div>
    );
  }

  return (
    <div className="stack" data-testid="admin-users">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Staff directory</h1>
        <Link href="/admin/users/invite">Invite staff</Link>
      </div>
      <div className="panel table-scroll">
        <div className="table-scroll" role="region" aria-label="Scrollable data table" tabIndex={0}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Roles</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {staff.map((u) => (
                <tr key={u.user_id}>
                  <td>{u.display_name}</td>
                  <td className="mono">{u.email}</td>
                  <td>{u.assignments.map((a) => a.role).join(", ")}</td>
                  <td>{u.account_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="panel stack">
        <h2>Pending invitations</h2>
        {invitations.length === 0 ? (
          <p className="muted">No invitations yet.</p>
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {invitations.map((inv) => (
                  <tr key={inv.invitation_id}>
                    <td>{inv.display_name}</td>
                    <td className="mono">{inv.work_email}</td>
                    <td>{inv.role}</td>
                    <td>{inv.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
