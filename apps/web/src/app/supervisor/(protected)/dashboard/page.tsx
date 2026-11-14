import { SupervisorOverview } from "@/components/dashboards/supervisor-overview";
import { requireRole } from "@/lib/server/authorization";

export default async function SupervisorDashboardPage() {
  const session = await requireRole("supervisor");
  return <SupervisorOverview session={session} />;
}
