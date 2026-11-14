import { OpsCombinedOverview } from "@/components/dashboards/ops-combined-overview";
import { requireAnyRole } from "@/lib/server/authorization";

export default async function SupervisorDashboardPage() {
  const session = await requireAnyRole(
    ["operator", "supervisor"],
    "supervisor",
  );
  return <OpsCombinedOverview session={session} />;
}
