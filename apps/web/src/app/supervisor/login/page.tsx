import { redirect } from "next/navigation";

export default function SupervisorLoginPage() {
  redirect("/login?portal=supervisor");
}
