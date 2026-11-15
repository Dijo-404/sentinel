import { CommandCenter } from "@/components/ops/command-center";
import { requireAnyRole } from "@/lib/server/authorization";

export default async function SupervisorCommandPage() {
  await requireAnyRole(["operator", "supervisor"], "supervisor");
  return <CommandCenter />;
}
