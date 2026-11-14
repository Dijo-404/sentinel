import { redirect } from "next/navigation";

export default function RiskLoginPage() {
  redirect("/login?portal=risk");
}
