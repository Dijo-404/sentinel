"use client";

import { useId, useState, type FormEvent } from "react";
import type { CaseClient } from "@/application/ports";
import { UiState } from "./ui-states";
import { LocalVoiceSubstitute } from "@/slots/local-voice-substitute";
import type { VoiceClient } from "@/application/ports";
import { PeerError } from "@/domain/types";

type Props = {
  title?: string;
  caseClient: CaseClient;
  voiceEnabled: boolean;
  voiceClient: VoiceClient | null;
};

export function IntakeForm({
  title = "Text intake",
  caseClient,
  voiceEnabled,
  voiceClient,
}: Props) {
  const formId = useId();
  const [message, setMessage] = useState("");
  const [language, setLanguage] = useState("en-IN");
  const [orderReference, setOrderReference] = useState("DEMO-ORDER-42");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [permission, setPermission] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setPermission(null);
    setCreatedId(null);
    try {
      const created = await caseClient.createCase(
        {
          message: message.trim(),
          language,
          order_reference: orderReference.trim(),
          channel: "web",
        },
        crypto.randomUUID(),
      );
      setCreatedId(created.case_id);
      // Cleared so a second click cannot file a duplicate complaint.
      setMessage("");
    } catch (err) {
      if (err instanceof PeerError && (err.httpStatus === 403 || err.code === "FORBIDDEN")) {
        setPermission(`${err.code}: ${err.message}`);
      } else if (err instanceof PeerError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : "Create failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stack">
      <h1>{title}</h1>
      <p className="muted">
        Tell us what went wrong with your payment. We verify it against your order and keep you
        updated.
      </p>
      <LocalVoiceSubstitute
        enabled={voiceEnabled}
        client={voiceClient}
        onTranscript={(text) => setMessage(text)}
      />
      <form className="panel stack" onSubmit={onSubmit} aria-labelledby={`${formId}-title`}>
        <h2 id={`${formId}-title`} className="sr-only">
          Create case
        </h2>
        <div className="intake-grid">
          <label>
            Language
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              aria-label="Language"
            >
              <option value="en-IN">English</option>
              <option value="ta-IN">Tamil</option>
            </select>
          </label>
          <label>
            Order reference
            <input
              value={orderReference}
              onChange={(e) => setOrderReference(e.target.value)}
              required
              aria-label="Order reference"
            />
          </label>
        </div>
        <label>
          Message
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
            rows={4}
            aria-label="Complaint message"
          />
        </label>
        <button type="submit" disabled={loading || !message.trim() || !orderReference.trim()}>
          Submit case
        </button>
      </form>
      {loading ? <UiState tone="loading" title="Submitting case…" /> : null}
      {error ? <UiState tone="error" title="Intake failed" detail={error} /> : null}
      {permission ? (
        <UiState tone="permission" title="Permission denied" detail={permission} />
      ) : null}
      {createdId ? (
        <UiState
          tone="empty"
          title="Case accepted"
          detail={`case_id=${createdId} · status=RECEIVED`}
        />
      ) : null}
    </div>
  );
}
