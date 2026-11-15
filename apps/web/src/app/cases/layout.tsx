import { requireRole } from "@/lib/server/authorization";

/** Legacy case timeline — customer session required (paired with /intake). */
export default async function CasesLayout({ children }: { children: React.ReactNode }) {
  await requireRole("customer");
  return children;
}
