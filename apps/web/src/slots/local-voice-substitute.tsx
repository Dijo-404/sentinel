"use client";

import { useState } from "react";
import type { VoiceClient } from "@/application/ports";
import { PeerError } from "@/domain/types";

type Props = {
  enabled: boolean;
  client: VoiceClient | null;
  onTranscript?: (text: string, language: string) => void;
};

/**
 * Local voice.v1 substitute. Disabled by default.
 * Never grants financial authority.
 */
export function LocalVoiceSubstitute({ enabled, client, onTranscript }: Props) {
  const [consent, setConsent] = useState(false);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  if (!enabled) {
    return (
      <section
        className="slot-box"
        data-testid="voice-slot"
        data-slot="voice.v1-disabled"
        aria-labelledby="voice-slot-title"
      >
        <h2 id="voice-slot-title">Voice slot</h2>
        <p className="muted">Voice disabled by default (optional voice.v1).</p>
      </section>
    );
  }

  async function run() {
    setError(null);
    setResult(null);
    if (!client) {
      setError("PEER_UNAVAILABLE: voice client not configured");
      return;
    }
    try {
      const out = await client.transcribe({
        language: "en-IN",
        text,
        consent,
      });
      setResult(out.original_text);
      onTranscript?.(out.original_text, out.language);
    } catch (err) {
      setError(
        err instanceof PeerError
          ? `${err.code}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Voice failed",
      );
    }
  }

  return (
    <section
      className="slot-box"
      data-testid="voice-slot"
      data-slot="voice.v1-local"
      aria-labelledby="voice-slot-title"
    >
      <h2 id="voice-slot-title">Voice slot (local substitute)</h2>
      <label>
        <span>Consent to process audio/text</span>
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
        />
      </label>
      <label>
        Text fallback
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-label="Voice text fallback"
        />
      </label>
      <button type="button" onClick={() => void run()}>
        Transcribe
      </button>
      {result ? <p role="status">Transcript: {result}</p> : null}
      {error ? (
        <p role="alert" data-testid="voice-slot-error">
          {error}
        </p>
      ) : null}
    </section>
  );
}
