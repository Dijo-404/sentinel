import type { PortalRole } from "../../../tests/stubs/identity";

/** identity.v1 role_id values for the six human portals. */
export type IdentityRoleId =
  "customer" | "merchant" | "operator" | "supervisor" | "risk_officer" | "platform_admin";

const PORTAL_TO_IDENTITY: Record<PortalRole, IdentityRoleId> = {
  customer: "customer",
  merchant: "merchant",
  operator: "operator",
  supervisor: "supervisor",
  risk: "risk_officer",
  admin: "platform_admin",
};

const IDENTITY_TO_PORTAL: Record<IdentityRoleId, PortalRole> = {
  customer: "customer",
  merchant: "merchant",
  operator: "operator",
  supervisor: "supervisor",
  risk_officer: "risk",
  platform_admin: "admin",
};

export function portalRoleToIdentity(role: PortalRole): IdentityRoleId {
  return PORTAL_TO_IDENTITY[role];
}

export function identityRoleToPortal(roleId: string): PortalRole | null {
  if (roleId in IDENTITY_TO_PORTAL) {
    return IDENTITY_TO_PORTAL[roleId as IdentityRoleId];
  }
  return null;
}

/** Map portal staff role_id from invite form to identity.v1 role_id. */
export function staffInviteRoleToIdentity(roleId: string): string {
  if (roleId === "risk") return "risk_officer";
  if (roleId === "admin") return "platform_admin";
  return roleId;
}
