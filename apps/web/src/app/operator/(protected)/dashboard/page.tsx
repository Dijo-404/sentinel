import { PortalDashboard } from "@/components/dashboards/portal-dashboard";
import { requireRole } from "@/lib/server/authorization";

export default async function OperatorDashboardPage() {
  const session = await requireRole("operator");
  return <PortalDashboard role="operator" session={session} />;
}
