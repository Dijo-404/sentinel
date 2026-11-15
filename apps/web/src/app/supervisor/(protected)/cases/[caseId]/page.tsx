import { requireAnyRole } from "@/lib/server/authorization";
import { SupervisorCaseDetail } from "./case-detail";

export default async function SupervisorCaseDetailPage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  const session = await requireAnyRole(["operator", "supervisor"], "supervisor");
  return (
    <SupervisorCaseDetail
      caseId={caseId}
      reviewerId={session.user.user_id}
      canApprove={session.assignment.role === "supervisor"}
    />
  );
}
