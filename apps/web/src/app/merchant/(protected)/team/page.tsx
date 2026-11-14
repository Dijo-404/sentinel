import { TeamPanel } from "@/components/merchant/team-panel";
import { requireRole } from "@/lib/server/authorization";

export default async function MerchantTeamPage() {
  const session = await requireRole("merchant");
  return <TeamPanel session={session} />;
}
