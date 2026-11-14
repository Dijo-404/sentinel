import { createSessionPeerProxy } from "../../_session-proxy";

export const dynamic = "force-dynamic";

const handlers = createSessionPeerProxy({
  envKey: "KNOWLEDGE_BASE_URL",
  peerLabel: "knowledge",
  requestIdPrefix: "web-bff-knowledge",
});

export const GET = handlers.GET;
export const POST = handlers.POST;
export const PUT = handlers.PUT;
export const PATCH = handlers.PATCH;
export const DELETE = handlers.DELETE;
