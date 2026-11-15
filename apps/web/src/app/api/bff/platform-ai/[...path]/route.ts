import { createSessionPeerProxy } from "../../_session-proxy";

export const dynamic = "force-dynamic";

const handlers = createSessionPeerProxy({
  envKey: "PLATFORM_AI_BASE_URL",
  peerLabel: "platform-ai",
  requestIdPrefix: "web-bff-platform-ai",
  // Peer authenticates opaque demo token; portal session stays the BFF gate.
  upstreamTokenRoles: ["admin"],
  upstreamTokenEnvKey: "PLATFORM_AI_SERVICE_TOKEN",
});

export const GET = handlers.GET;
export const POST = handlers.POST;
export const PUT = handlers.PUT;
export const PATCH = handlers.PATCH;
export const DELETE = handlers.DELETE;
