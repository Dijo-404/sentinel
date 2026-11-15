import { NotificationsPanel } from "@/components/customer/notifications-panel";
import { PeerError } from "@/domain/types";
import { readSessionId } from "@/lib/server/auth";
import { requireRole } from "@/lib/server/authorization";
import { getIdentityClient } from "@/lib/server/identity-client";

export default async function CustomerNotificationsPage() {
  await requireRole("customer");
  const sessionId = await readSessionId();
  if (!sessionId) {
    return <NotificationsPanel error={{ code: "UNAUTHORIZED", message: "Session required" }} />;
  }

  try {
    const listed = await getIdentityClient().listNotifications(sessionId);
    return <NotificationsPanel notifications={listed.notifications} />;
  } catch (err) {
    const message = err instanceof PeerError ? err.message : "Identity peer unavailable";
    return (
      <NotificationsPanel
        error={{
          code: err instanceof PeerError ? err.code : "PEER_UNAVAILABLE",
          message,
        }}
      />
    );
  }
}
