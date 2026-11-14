import { OperatorDashboardClient } from "./dashboard-client";
import { requireRole } from "@/lib/server/authorization";

export default async function OperatorDashboardPage() {
  const session = await requireRole("operator");
  return <OperatorDashboardClient session={session} />;
}
