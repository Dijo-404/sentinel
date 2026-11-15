import { createSessionPeerProxy } from "../../_session-proxy";

export const dynamic = "force-dynamic";

const handlers = createSessionPeerProxy({
  envKey: "EVALS_BASE_URL",
  peerLabel: "evals",
  requestIdPrefix: "web-bff-evals",
  // Peer authenticates opaque demo token; portal session stays the BFF gate.
  upstreamTokenEnvKey: "EVALS_SERVICE_TOKEN",
});

export const GET = handlers.GET;
export const POST = handlers.POST;
export const PUT = handlers.PUT;
export const PATCH = handlers.PATCH;
export const DELETE = handlers.DELETE;
