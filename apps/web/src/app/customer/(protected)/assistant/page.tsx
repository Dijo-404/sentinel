import { AssistantPanel } from "@/components/ops/assistant-panel";
import { requireRole } from "@/lib/server/authorization";

export default async function CustomerAssistantPage() {
  await requireRole("customer");
  return <AssistantPanel role="customer" testId="customer-assistant" />;
}
