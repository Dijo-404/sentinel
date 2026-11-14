import type { VoiceClient } from "@/application/ports";
import { PeerError, type VoiceResult } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type VoicePeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateVoiceResult(json: unknown, requestId: string): VoiceResult {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Voice result is not an object",
      requestId,
    );
  }
  const o = json as Record<string, unknown>;
  if (
    typeof o.original_text !== "string" ||
    typeof o.language !== "string" ||
    typeof o.ambiguous !== "boolean" ||
    !Array.isArray(o.reason_codes)
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Voice result missing required fields",
      requestId,
    );
  }
  if (!o.reason_codes.every((c) => typeof c === "string")) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Voice reason_codes must be strings",
      requestId,
    );
  }
  const result: VoiceResult = {
    original_text: o.original_text,
    language: o.language,
    ambiguous: o.ambiguous,
    reason_codes: o.reason_codes as string[],
  };
  if (typeof o.evidence_mode === "string" && o.evidence_mode.trim()) {
    result.evidence_mode = o.evidence_mode.trim();
  }
  return result;
}

function validateCapabilitiesMode(
  json: unknown,
  requestId: string,
): "recorded" | "live" {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Voice capabilities is not an object",
      requestId,
    );
  }
  const mode = (json as { mode?: unknown }).mode;
  if (typeof mode !== "string" || !mode.trim()) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Voice capabilities missing mode",
      requestId,
    );
  }
  // Fixture / recorded Sarvam responses → recorded; live provider → live.
  return mode.trim() === "fixture" ? "recorded" : "live";
}

export function createRealPeerVoiceClient(
  options: VoicePeerOptions,
): VoiceClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "voice",
  });

  return {
    async transcribe(body) {
      const result = await request(
        "POST",
        "/v1/transcribe",
        validateVoiceResult,
        body,
      );
      if (result.evidence_mode) {
        return result;
      }
      const evidence_mode = await request(
        "GET",
        "/v1/capabilities",
        validateCapabilitiesMode,
      );
      return { ...result, evidence_mode };
    },
  };
}

/** Browser path: same-origin BFF with session cookie. */
export function createBffVoiceClient(options?: {
  fetchImpl?: typeof fetch;
}): VoiceClient {
  return createRealPeerVoiceClient({
    baseUrl: "/api/bff/voice",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
