import { createSessionPeerProxy } from "../../_session-proxy";

export const dynamic = "force-dynamic";

const handlers = createSessionPeerProxy({
  envKey: "MERCHANT_ANALYTICS_BASE_URL",
  peerLabel: "merchant-analytics",
  requestIdPrefix: "web-bff-merchant-analytics",
  // Peer authenticates opaque demo token; portal session stays the BFF gate.
  upstreamTokenEnvKey: "MERCHANT_ANALYTICS_SERVICE_TOKEN",
});

export const GET = handlers.GET;
export const POST = handlers.POST;
export const PUT = handlers.PUT;
export const PATCH = handlers.PATCH;
export const DELETE = handlers.DELETE;
