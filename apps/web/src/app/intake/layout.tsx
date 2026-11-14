import { requireRole } from "@/lib/server/authorization";

/** Legacy intake — customer session required. */
export default async function IntakeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requireRole("customer");
  return children;
}
