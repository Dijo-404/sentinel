import { PortalDashboard } from "@/components/dashboards/portal-dashboard";
import { requireRole } from "@/lib/server/authorization";

export default async function MerchantDashboardPage() {
  const session = await requireRole("merchant");
  return <PortalDashboard role="merchant" session={session} />;
}
