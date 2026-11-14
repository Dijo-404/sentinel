import type { PortalRole } from "../../tests/stubs/identity";

/** Advisory UI permission projection only — never authoritative. */
export function previewPermissions(
  role: Exclude<PortalRole, "customer">,
): string[] {
  switch (role) {
    case "merchant":
      return [
        "View merchant transactions and settlements",
        "Request refunds (not ledger authority)",
        "Manage merchant team tasks",
      ];
    case "operator":
      return [
        "Claim and work support cases",
        "View scoped evidence",
        "Escalate — no financial approval",
      ];
    case "supervisor":
      return [
        "Exact approve/reject on ledger proposals",
        "View approval history and audit",
        "No payload edits after proposal",
      ];
    case "risk":
      return [
        "Open fraud investigations",
        "Place/clear holds (not money approval)",
        "Restricted evidence views",
      ];
    case "admin":
      return [
        "Invite and manage staff",
        "Grant/revoke scoped roles",
        "View identity audit and security controls",
      ];
  }
}

export const PORTAL_META: Record<
  PortalRole,
  { title: string; description: string }
> = {
  customer: {
    title: "Customer portal",
    description: "Report payment problems and track verified resolutions.",
  },
  merchant: {
    title: "Merchant portal",
    description: "Settlements, exceptions and refund requests for your business.",
  },
  operator: {
    title: "Support Operator",
    description: "Investigate exceptions and assist customers.",
  },
  supervisor: {
    title: "Supervisor",
    description: "Exact financial approvals and team oversight.",
  },
  risk: {
    title: "Risk & Fraud",
    description: "Investigate suspicious activity and manage holds.",
  },
  admin: {
    title: "Platform Admin",
    description: "Provision staff, roles, tenants and platform controls.",
  },
};
