import { requireAnyRole } from "@/lib/server/authorization";
import { DecisionView } from "./decision-view";

export default async function SupervisorApprovalDetailPage({
  params,
}: {
  params: Promise<{ actionId: string }>;
}) {
  const { actionId } = await params;
  const session = await requireAnyRole(["operator", "supervisor"], "supervisor");
  return <DecisionView actionId={actionId} canDecide={session.assignment.role === "supervisor"} />;
}
