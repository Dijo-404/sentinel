import { PortalDashboard } from "@/components/dashboards/portal-dashboard";
import { requireRole } from "@/lib/server/authorization";

export default async function AdminDashboardPage() {
  const session = await requireRole("admin");
  return <PortalDashboard role="admin" session={session} />;
}
