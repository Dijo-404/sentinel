import { describe, expect, it, vi } from "vitest";
import { createCaseApiDecideClient } from "../src/adapters/case-api-client.js";
import { createActionLedgerDecideClient } from "../src/adapters/action-ledger-client.js";
import { DecisionClientError } from "../src/domain/errors.js";
import previewBundle from "../fixtures/preview-bundle.json";

const request = {
  decision: "APPROVE" as const,
  action_digest: previewBundle.expected_sha256,
  case_revision: 1,
  policy_version: "demo-policy-v1",
  expires_at: previewBundle.decision_expires_at,
};

describe("real-peer adapters", () => {
  it("case-api adapter posts decisions and surfaces peer failures without fixture fallback", async () => {
    const fetchImpl = vi.fn(async () =>
      new Response(
        JSON.stringify({
          code: "PEER_UNAVAILABLE",
          message: "Required peer unavailable",
          request_id: "req-1",
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      ),
    );

    const decide = createCaseApiDecideClient({
      baseUrl: "https://case-api.example/",
      bearerToken: "synthetic-supervisor-token",
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    await expect(decide("action-demo-1", request)).rejects.toBeInstanceOf(
      DecisionClientError,
    );
    expect(fetchImpl).toHaveBeenCalledWith(
      "https://case-api.example/v1/ops/actions/action-demo-1/decisions",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer synthetic-supervisor-token",
        }),
      }),
    );
  });

  it("action-ledger adapter rejects missing configuration instead of fixture success", async () => {
    const decide = createActionLedgerDecideClient({
      baseUrl: "",
      bearerToken: "",
    });
    await expect(decide("action-demo-1", request)).rejects.toMatchObject({
      uiCode: "UNAVAILABLE",
    });
  });

  it("action-ledger adapter returns Approval on 200", async () => {
    const fetchImpl = vi.fn(async () =>
      new Response(JSON.stringify(previewBundle.approval_response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const decide = createActionLedgerDecideClient({
      baseUrl: "https://ledger.example/",
      bearerToken: "synthetic-supervisor-token",
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    await expect(decide("action-demo-1", request)).resolves.toMatchObject({
      approval_id: "approval-demo-1",
    });
  });
});
