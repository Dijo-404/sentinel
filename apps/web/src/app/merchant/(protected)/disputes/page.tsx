import { DisputesPanel } from "@/components/merchant/disputes-panel";
import { requireRole } from "@/lib/server/authorization";

export default async function MerchantDisputesPage() {
  const session = await requireRole("merchant");
  return <DisputesPanel session={session} />;
}
