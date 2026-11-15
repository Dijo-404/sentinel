import { ProfilePanel } from "@/components/customer/profile-panel";
import { PeerError } from "@/domain/types";
import { toPublicProfileUser } from "@/lib/identity-public";
import { readSessionId } from "@/lib/server/auth";
import { requireRole } from "@/lib/server/authorization";
import { getIdentityClient } from "@/lib/server/identity-client";

export default async function CustomerProfilePage() {
  await requireRole("customer");
  const sessionId = await readSessionId();
  if (!sessionId) {
    return <ProfilePanel error={{ code: "UNAUTHORIZED", message: "Session required" }} />;
  }

  try {
    const me = await getIdentityClient().getMe(sessionId);
    if (!me) {
      return <ProfilePanel error={{ code: "UNAUTHORIZED", message: "Session required" }} />;
    }
    return <ProfilePanel user={toPublicProfileUser(me.user)} />;
  } catch (err) {
    const message = err instanceof PeerError ? err.message : "Identity peer unavailable";
    return (
      <ProfilePanel
        error={{
          code: err instanceof PeerError ? err.code : "PEER_UNAVAILABLE",
          message,
        }}
      />
    );
  }
}
