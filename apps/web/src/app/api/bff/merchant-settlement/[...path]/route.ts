import { createSessionPeerProxy } from "../../_session-proxy";

export const dynamic = "force-dynamic";

const handlers = createSessionPeerProxy({
  envKey: "MERCHANT_SETTLEMENT_BASE_URL",
  peerLabel: "merchant-settlement",
  requestIdPrefix: "web-bff-merchant-settlement",
  // Peer authenticates opaque demo token; portal session stays the BFF gate.
  upstreamTokenRoles: ["merchant"],
  upstreamTokenEnvKey: "MERCHANT_SETTLEMENT_SERVICE_TOKEN",
});

export const GET = handlers.GET;
export const POST = handlers.POST;
export const PUT = handlers.PUT;
export const PATCH = handlers.PATCH;
export const DELETE = handlers.DELETE;
