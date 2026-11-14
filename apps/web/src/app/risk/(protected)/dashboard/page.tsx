import { PortalDashboard } from "@/components/dashboards/portal-dashboard";
import { requireRole } from "@/lib/server/authorization";

export default async function RiskDashboardPage() {
  const session = await requireRole("risk");
  return <PortalDashboard role="risk" session={session} />;
}
