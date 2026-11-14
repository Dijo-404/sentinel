import { ExceptionsPanel } from "@/components/merchant/exceptions-panel";
import { requireRole } from "@/lib/server/authorization";

export default async function MerchantExceptionsPage() {
  const session = await requireRole("merchant");
  return <ExceptionsPanel session={session} />;
}
