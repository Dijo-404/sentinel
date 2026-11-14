import { AnalyticsPanel } from "@/components/merchant/analytics-panel";
import { requireRole } from "@/lib/server/authorization";

export default async function MerchantAnalyticsPage() {
  const session = await requireRole("merchant");
  return <AnalyticsPanel session={session} />;
}
