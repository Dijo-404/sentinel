import { createSessionPeerProxy } from "../../_session-proxy";

export const dynamic = "force-dynamic";

const handlers = createSessionPeerProxy({
  envKey: "ASSISTANT_BASE_URL",
  peerLabel: "assistant",
  requestIdPrefix: "web-bff-assistant",
  // Peer authenticates opaque demo token; portal session stays the BFF gate.
  upstreamTokenEnvKey: "ASSISTANT_SERVICE_TOKEN",
  upstreamTokenRolePrefix: "ASSISTANT_TOKEN_",
});

export const GET = handlers.GET;
export const POST = handlers.POST;
export const PUT = handlers.PUT;
export const PATCH = handlers.PATCH;
export const DELETE = handlers.DELETE;
