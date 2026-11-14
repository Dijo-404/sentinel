import { MerchantOverview } from "@/components/dashboards/merchant-overview";
import { requireRole } from "@/lib/server/authorization";

export default async function MerchantDashboardPage() {
  const session = await requireRole("merchant");
  return <MerchantOverview session={session} />;
}
