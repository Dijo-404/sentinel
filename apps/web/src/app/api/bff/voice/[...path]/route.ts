import { createSessionPeerProxy } from "../../_session-proxy";

export const dynamic = "force-dynamic";

const handlers = createSessionPeerProxy({
  envKey: "VOICE_BASE_URL",
  peerLabel: "voice",
  requestIdPrefix: "web-bff-voice",
  // Voice peer authenticates voice-demo-token; portal session stays the BFF gate.
  upstreamTokenEnvKey: "VOICE_SERVICE_TOKEN",
});

export const GET = handlers.GET;
export const POST = handlers.POST;
export const PUT = handlers.PUT;
export const PATCH = handlers.PATCH;
export const DELETE = handlers.DELETE;
