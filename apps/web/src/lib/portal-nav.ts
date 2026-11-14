import type { PortalRole } from "../../tests/stubs/identity";
import type { NavItem } from "@/components/layout/protected-shell";

export const PORTAL_NAV: Record<PortalRole, NavItem[]> = {
  customer: [
    { href: "/customer/dashboard", label: "Dashboard" },
    { href: "/customer/transactions", label: "Transactions" },
    { href: "/customer/report", label: "Report" },
    { href: "/customer/cases", label: "Cases" },
    { href: "/intake", label: "Legacy intake" },
  ],
  merchant: [
    { href: "/merchant/dashboard", label: "Dashboard" },
    { href: "/merchant/transactions", label: "Transactions" },
    { href: "/merchant/settlements", label: "Settlements" },
    { href: "/merchant/refunds", label: "Refunds" },
  ],
  operator: [
    { href: "/operator/dashboard", label: "Dashboard" },
    { href: "/operator/queue", label: "Queue" },
    { href: "/ops", label: "Legacy ops" },
    { href: "/operator/escalations", label: "Escalations" },
  ],
  supervisor: [
    { href: "/supervisor/dashboard", label: "Dashboard" },
    { href: "/supervisor/approvals", label: "Approvals" },
    { href: "/supervisor/history", label: "History" },
    { href: "/supervisor/audit", label: "Audit" },
  ],
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
