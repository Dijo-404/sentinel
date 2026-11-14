import { OpsCombinedOverview } from "@/components/dashboards/ops-combined-overview";
import { requireAnyRole } from "@/lib/server/authorization";

export default async function OperatorDashboardPage() {
  const session = await requireAnyRole(["operator", "supervisor"], "operator");
  return <OpsCombinedOverview session={session} />;
}
