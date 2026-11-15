import { requireAnyRole } from "@/lib/server/authorization";

/** Legacy ops — operator or supervisor session required. */
export default async function OpsLayout({ children }: { children: React.ReactNode }) {
  await requireAnyRole(["operator", "supervisor"], "operator");
  return children;
}
