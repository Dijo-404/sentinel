import { createSessionPeerProxy } from "../../_session-proxy";

export const dynamic = "force-dynamic";

const handlers = createSessionPeerProxy({
  envKey: "POLICY_BASE_URL",
  peerLabel: "policy",
  requestIdPrefix: "web-bff-policy",
});

export const GET = handlers.GET;
export const POST = handlers.POST;
export const PUT = handlers.PUT;
export const PATCH = handlers.PATCH;
export const DELETE = handlers.DELETE;
