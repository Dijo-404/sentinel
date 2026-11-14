import { SettingsPanel } from "@/components/merchant/settings-panel";
import { requireRole } from "@/lib/server/authorization";

export default async function MerchantSettingsPage() {
  const session = await requireRole("merchant");
  return <SettingsPanel session={session} />;
}
