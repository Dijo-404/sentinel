import type { PortalRole } from "../../tests/stubs/identity";
import type { NavItem } from "@/components/layout/protected-shell";

/**
 * Shared ops workspace nav (operator ∪ supervisor menus from roles.md).
 * Dashboard stays portal-local; other items use canonical routes so both
 * roles land on the same screens (layouts accept either role).
 */
export function opsPortalNav(portal: "operator" | "supervisor"): NavItem[] {
  return [
    { href: `/${portal}/dashboard`, label: "Dashboard" },
    { href: "/supervisor/command", label: "Command center" },
    { href: "/operator/queue", label: "Queue" },
    { href: "/supervisor/approvals", label: "Approvals" },
    { href: "/operator/escalations", label: "Escalations" },
    { href: "/operator/messages", label: "Messages" },
    { href: "/operator/assistant", label: "Assistant" },
    { href: "/operator/knowledge", label: "Knowledge" },
    { href: "/operator/activity", label: "Activity" },
    { href: "/supervisor/history", label: "History" },
    { href: "/supervisor/team", label: "Team" },
    { href: "/supervisor/audit", label: "Audit" },
  ];
}

export const PORTAL_NAV: Record<PortalRole, NavItem[]> = {
  customer: [
    { href: "/customer/dashboard", label: "Dashboard" },
    { href: "/customer/transactions", label: "Transactions" },
    { href: "/customer/report", label: "Report" },
    { href: "/customer/cases", label: "Cases" },
    { href: "/customer/profile", label: "Profile" },
    { href: "/customer/notifications", label: "Notifications" },
  ],
  merchant: [
    { href: "/merchant/dashboard", label: "Dashboard" },
    { href: "/merchant/transactions", label: "Transactions" },
    { href: "/merchant/settlements", label: "Settlements" },
    { href: "/merchant/refunds", label: "Refunds" },
  ],
  operator: opsPortalNav("operator"),
  supervisor: opsPortalNav("supervisor"),
  risk: [
    { href: "/risk/dashboard", label: "Dashboard" },
    { href: "/risk/queue", label: "Queue" },
    { href: "/risk/holds", label: "Holds" },
    { href: "/risk/audit", label: "Audit" },
  ],
  admin: [
    { href: "/admin/dashboard", label: "Dashboard" },
    { href: "/admin/users", label: "Users" },
    { href: "/admin/users/invite", label: "Invite" },
    { href: "/admin/roles", label: "Roles" },
    { href: "/admin/audit", label: "Audit" },
  ],
};
