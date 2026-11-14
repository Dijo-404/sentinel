import { InviteStaffForm } from "@/components/identity/invite-staff-form";
import { requireRole } from "@/lib/server/authorization";

export default async function AdminInvitePage() {
  await requireRole("admin");
  return <InviteStaffForm />;
}
