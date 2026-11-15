import { describe, expect, it } from "vitest";
import { createCaseApiStub, STUB_SCENARIOS } from "./stubs/case-api";
import { APPROVAL_UI_SCENARIOS, createApprovalUiStub } from "./stubs/approval-ui";
import { VOICE_SCENARIOS, createVoiceStub } from "./stubs/voice";
import { PeerError } from "@/domain/types";
import { createRealPeerCaseClient } from "@/adapters/real-peer-case-client";
import { createShellRuntime } from "@/adapters/composition";
import { validateCase } from "@/adapters/validate";

describe("peer stubs cover required scenarios", () => {
  it("declares all case-api scenarios", () => {
    expect(STUB_SCENARIOS).toEqual([
      "valid",
      "unavailable",
      "malformed",
      "unauthorized_or_out_of_scope",
    ]);
    expect(APPROVAL_UI_SCENARIOS).toHaveLength(4);
    expect(VOICE_SCENARIOS).toHaveLength(4);
  });

  it("valid case stub returns demo case", async () => {
    const client = createCaseApiStub("valid");
    const c = await client.getCase("case-demo-42");
    expect(c.status).toBe("WAITING_APPROVAL");
  });

  it("unavailable / unauthorized stubs throw visibly", async () => {
    try {
      await createCaseApiStub("unavailable").getCase("x");
      expect.unreachable("expected unavailable");
    } catch (err) {
      expect(err).toBeInstanceOf(PeerError);
      expect((err as PeerError).code).toBe("PEER_UNAVAILABLE");
    }
    try {
      await createCaseApiStub("unauthorized_or_out_of_scope").listOpsCases();
      expect.unreachable("expected forbidden");
    } catch (err) {
      expect(err).toBeInstanceOf(PeerError);
      expect((err as PeerError).code).toBe("FORBIDDEN");
    }
  });

  it("malformed stub fails validation", () => {
    expect(() => validateCase({ case_id: "x" }, "req-malformed")).toThrow(PeerError);
  });

  it("approval and voice stubs expose failure modes", async () => {
    const unavailable = createApprovalUiStub("unavailable");
    expect(unavailable.status).toBe("error");
    await expect(
      createVoiceStub("unavailable").transcribe({
        language: "en-IN",
        text: "hi",
        consent: true,
      }),
    ).rejects.toMatchObject({ code: "PEER_UNAVAILABLE" });
  });
});

describe("real-peer adapter", () => {
  it("surfaces network failure without fixture fallback", async () => {
    const client = createRealPeerCaseClient({
      baseUrl: "http://127.0.0.1:9",
      bearerToken: "token",
      fetchImpl: async () => {
        throw new Error("connect refused");
      },
    });
    await expect(client.getCase("case-demo-42")).rejects.toMatchObject({
      code: "PEER_UNAVAILABLE",
    });
  });

  it("surfaces 403 without switching to fixture", async () => {
    const client = createRealPeerCaseClient({
      baseUrl: "http://case.test",
      bearerToken: "token",
      fetchImpl: async () =>
        new Response(
          JSON.stringify({
            code: "FORBIDDEN",
            message: "Out of scope",
            request_id: "r1",
          }),
          { status: 403 },
        ),
    });
    await expect(client.listOpsCases()).rejects.toMatchObject({
      code: "FORBIDDEN",
    });
  });

  it("rejects malformed JSON body", async () => {
    const client = createRealPeerCaseClient({
      baseUrl: "http://case.test",
      bearerToken: "token",
      fetchImpl: async () => new Response("{not-json", { status: 200 }),
    });
    await expect(client.getCase("case-demo-42")).rejects.toMatchObject({
      code: "MALFORMED_PEER_RESPONSE",
    });
  });

  it("real-peers composition does not silently use fixture success", async () => {
    const runtime = createShellRuntime(
      {
        mode: "real-peers",
        voiceEnabled: false,
        contractVersion: "sentinel.task-contracts.v1",
        contractSha256: "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb",
        caseApiBaseUrl: "http://missing.peer",
        bearerToken: "x",
        principal: {
          principal_id: "p",
          tenant_id: "t",
          roles: ["operator"],
          subject_refs: [],
          case_ids: [],
        },
      },
      {
        fetchImpl: async () => {
          throw new Error("peer down");
        },
      },
    );
    await expect(runtime.caseClient.getCase("case-demo-42")).rejects.toMatchObject({
      code: "PEER_UNAVAILABLE",
    });
  });
});
