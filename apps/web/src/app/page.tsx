import { LandingPage } from "@/components/marketing/landing-page";
import { getAuthSession, portalPath } from "@/lib/server/auth";

export default async function HomePage() {
  const session = await getAuthSession();
  const dashboardHref = session ? portalPath(session.assignment.role) : null;

  return <LandingPage dashboardHref={dashboardHref} />;
}
