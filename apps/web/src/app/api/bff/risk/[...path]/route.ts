import { createSessionPeerProxy } from "../../_session-proxy";

export const dynamic = "force-dynamic";

const handlers = createSessionPeerProxy({
  envKey: "RISK_BASE_URL",
  peerLabel: "risk",
  requestIdPrefix: "web-bff-risk",
  // Peer authenticates opaque demo token; portal session stays the BFF gate.
  upstreamTokenRoles: ["risk"],
  upstreamTokenEnvKey: "RISK_SERVICE_TOKEN",
});

export const GET = handlers.GET;
export const POST = handlers.POST;
export const PUT = handlers.PUT;
export const PATCH = handlers.PATCH;
export const DELETE = handlers.DELETE;
