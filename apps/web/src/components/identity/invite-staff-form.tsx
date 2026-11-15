"use client";

import { useActionState, useState } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import { inviteStaffAction, type ActionResult } from "@/lib/server/auth-actions";
import { PermissionPreview } from "./permission-preview";

const STAFF_OPTIONS: Array<{
  role_id: Exclude<PortalRole, "customer">;
  label: string;
}> = [
  { role_id: "merchant", label: "Merchant Staff" },
  { role_id: "operator", label: "Support Operator" },
  { role_id: "supervisor", label: "Supervisor" },
  { role_id: "risk", label: "Risk Officer" },
  { role_id: "admin", label: "Platform Admin" },
];

const initial: ActionResult | null = null;

export function InviteStaffForm() {
  const [state, formAction, pending] = useActionState(inviteStaffAction, initial);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [tenant, setTenant] = useState("tenant-demo");
  const [reason, setReason] = useState("");
  const [role, setRole] = useState<Exclude<PortalRole, "customer">>("operator");

  return (
    <div className="stack" data-testid="invite-staff-form">
      <form action={formAction} className="panel stack">
        <h1>Invite staff</h1>
        <p className="muted">Customer accounts cannot be invited here. No public staff sign-up.</p>

        <label>
          Full name
          <input
            name="display_name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            data-testid="invite-name"
          />
        </label>
        <label>
          Work email
          <input
            name="work_email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            data-testid="invite-email"
          />
        </label>
        <label>
          Tenant
          <input
            name="tenant_id"
            value={tenant}
            onChange={(e) => setTenant(e.target.value)}
            required
            data-testid="invite-tenant"
          />
        </label>
        <label>
          Role
          <select
            name="role_id"
            value={role}
            onChange={(e) => setRole(e.target.value as Exclude<PortalRole, "customer">)}
            data-testid="invite-role"
          >
            {STAFF_OPTIONS.map((opt) => (
              <option key={opt.role_id} value={opt.role_id}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Reason
          <textarea
            name="reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            data-testid="invite-reason"
          />
        </label>
        <input type="hidden" name="idempotency_key" value={`invite-${Date.now()}`} />

        {state && !state.ok ? (
          <div className="state-banner" data-tone="error" role="alert">
            {state.message}
          </div>
        ) : null}

        <button type="submit" disabled={pending} data-testid="invite-submit">
          {pending ? "Sending…" : "Send invitation"}
        </button>
      </form>

      <PermissionPreview role={role} />
    </div>
  );
}
