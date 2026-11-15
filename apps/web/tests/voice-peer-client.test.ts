import { describe, expect, it, vi } from "vitest";
import { createBffVoiceClient, createRealPeerVoiceClient } from "@/adapters/real-peer-voice-client";
import { createShellRuntime, loadShellConfig } from "@/adapters/composition";
import { PeerError } from "@/domain/types";

describe("voice peer client", () => {
  it("transcribe POSTs /v1/transcribe and labels evidence_mode from capabilities", async () => {
    const fetchImpl = vi.fn().mockImplementation((url: string) => {
      const path = String(url);
      if (path.includes("/v1/capabilities")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              contract_version: "sentinel.task-contracts.v1",
              component: "voice",
              mode: "fixture",
              port: "voice.v1",
            }),
            { status: 200, headers: { "content-type": "application/json" } },
          ),
        );
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            original_text: "paid twice",
            language: "en-IN",
            ambiguous: false,
            reason_codes: ["NO_FINANCIAL_AUTHORITY"],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );
    });

    const client = createRealPeerVoiceClient({
      baseUrl: "http://voice.test",
      bearerToken: "tok",
      fetchImpl: fetchImpl as typeof fetch,
    });

    const result = await client.transcribe({
      language: "en-IN",
      text: "paid twice",
      consent: true,
    });

    expect(result.original_text).toBe("paid twice");
    expect(result.evidence_mode).toBe("recorded");
    expect(String(fetchImpl.mock.calls[0]![0])).toContain("/v1/transcribe");
    expect(String(fetchImpl.mock.calls[1]![0])).toContain("/v1/capabilities");
  });

  it("labels live when peer mode is real-peers", async () => {
    const fetchImpl = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/v1/capabilities")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              contract_version: "v1",
              component: "voice",
              mode: "real-peers",
              port: "voice.v1",
            }),
            { status: 200, headers: { "content-type": "application/json" } },
          ),
        );
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            original_text: "ok",
            language: "en-IN",
            ambiguous: false,
            reason_codes: [],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );
    });

    const client = createRealPeerVoiceClient({
      baseUrl: "http://voice.test",
      bearerToken: "tok",
      fetchImpl: fetchImpl as typeof fetch,
    });
    const result = await client.transcribe({
      language: "en-IN",
      text: "ok",
      consent: true,
    });
    expect(result.evidence_mode).toBe("live");
  });

  it("fails closed on peer down — no fake live transcript", async () => {
    const client = createRealPeerVoiceClient({
      baseUrl: "http://voice.test",
      bearerToken: "tok",
      fetchImpl: async () => {
        throw new Error("ECONNREFUSED");
      },
    });
    await expect(
      client.transcribe({
        language: "en-IN",
        text: "x",
        consent: true,
      }),
    ).rejects.toMatchObject({ code: "PEER_UNAVAILABLE" });
  });

  it("rejects malformed transcribe body", async () => {
    const client = createRealPeerVoiceClient({
      baseUrl: "http://voice.test",
      bearerToken: "tok",
      fetchImpl: async () =>
        new Response(JSON.stringify({ language: "en-IN" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    });
    await expect(
      client.transcribe({ language: "en-IN", text: "x", consent: true }),
    ).rejects.toBeInstanceOf(PeerError);
    await expect(
      client.transcribe({ language: "en-IN", text: "x", consent: true }),
    ).rejects.toMatchObject({ code: "MALFORMED_PEER_RESPONSE" });
  });

  it("BFF client targets /api/bff/voice with credentials", async () => {
    const fetchImpl = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/v1/capabilities")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              mode: "fixture",
              component: "voice",
              port: "voice.v1",
              contract_version: "v1",
            }),
            { status: 200, headers: { "content-type": "application/json" } },
          ),
        );
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            original_text: "hi",
            language: "en-IN",
            ambiguous: false,
            reason_codes: [],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );
    });
    const client = createBffVoiceClient({ fetchImpl: fetchImpl as typeof fetch });
    await client.transcribe({ language: "en-IN", text: "hi", consent: true });
    expect(String(fetchImpl.mock.calls[0]![0])).toContain("/api/bff/voice/");
    expect(fetchImpl.mock.calls[0]![1]).toMatchObject({
      credentials: "same-origin",
    });
  });

  it("real-peers composition wires BFF voice client when enabled", async () => {
    const fetchImpl = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/v1/capabilities")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              mode: "fixture",
              component: "voice",
              port: "voice.v1",
              contract_version: "v1",
            }),
            { status: 200, headers: { "content-type": "application/json" } },
          ),
        );
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            original_text: "wired",
            language: "en-IN",
            ambiguous: false,
            reason_codes: [],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );
    });

    const runtime = createShellRuntime(
      loadShellConfig({
        NEXT_PUBLIC_SHELL_MODE: "real-peers",
        NEXT_PUBLIC_VOICE_ENABLED: "true",
        CASE_API_BASE_URL: "http://127.0.0.1:8080",
      }),
      { fetchImpl: fetchImpl as typeof fetch },
    );

    expect(runtime.config.voiceEnabled).toBe(true);
    expect(runtime.voiceClient).not.toBeNull();
    const result = await runtime.voiceClient!.transcribe({
      language: "en-IN",
      text: "wired",
      consent: true,
    });
    expect(result.original_text).toBe("wired");
    expect(result.evidence_mode).toBe("recorded");
    expect(String(fetchImpl.mock.calls[0]![0])).toContain("/api/bff/voice/");
  });
});
