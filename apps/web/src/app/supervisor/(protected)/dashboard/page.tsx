import { PortalDashboard } from "@/components/dashboards/portal-dashboard";
import { requireRole } from "@/lib/server/authorization";

export default async function SupervisorDashboardPage() {
  const session = await requireRole("supervisor");
  return <PortalDashboard role="supervisor" session={session} />;
}
