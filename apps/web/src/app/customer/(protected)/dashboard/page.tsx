import { PortalDashboard } from "@/components/dashboards/portal-dashboard";
import { requireRole } from "@/lib/server/authorization";

export default async function CustomerDashboardPage() {
  const session = await requireRole("customer");
  return <PortalDashboard role="customer" session={session} />;
}
