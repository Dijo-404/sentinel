import type { VoiceClient } from "@/application/ports";
import { PeerError, type VoiceRequest, type VoiceResult } from "@/domain/types";

export type StubVoice =
  | "valid"
  | "unavailable"
  | "malformed"
  | "unauthorized_or_out_of_scope";

/** Local voice.v1 double. Optional; shell defaults to disabled. */
export function createVoiceStub(scenario: StubVoice = "valid"): VoiceClient {
  if (scenario === "unavailable") {
    return {
      async transcribe() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "voice peer unavailable",
          "req-voice-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "unauthorized_or_out_of_scope") {
    return {
      async transcribe() {
        throw new PeerError(
          "FORBIDDEN",
          "voice out of scope or consent missing",
          "req-voice-forbidden",
          403,
        );
      },
    };
  }
  if (scenario === "malformed") {
    return {
      async transcribe() {
        return { language: "en-IN" } as unknown as VoiceResult;
      },
    };
  }
  return {
    async transcribe(request: VoiceRequest): Promise<VoiceResult> {
      if (!request.consent) {
        throw new PeerError(
          "CONSENT_REQUIRED",
          "Voice requires explicit consent",
          "req-voice-consent",
          422,
        );
      }
      const hasAudio = Boolean(request.audio_uri);
      const hasText = Boolean(request.text);
      if (hasAudio === hasText) {
        throw new PeerError(
          "INVALID_INPUT",
          "Provide exactly one of audio_uri or text",
          "req-voice-input",
          422,
        );
      }
      return {
        original_text: request.text ?? "[fixture transcript]",
        language: request.language,
        ambiguous: false,
        reason_codes: [],
      };
    },
  };
}

export const VOICE_SCENARIOS: StubVoice[] = [
  "valid",
  "unavailable",
  "malformed",
  "unauthorized_or_out_of_scope",
];
