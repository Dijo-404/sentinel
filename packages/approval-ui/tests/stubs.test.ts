import { describe, expect, it } from "vitest";
import { DecisionClientError } from "../src/domain/errors.js";
import previewBundle from "../fixtures/preview-bundle.json";
import { createActionLedgerStub } from "./stubs/action-ledger.js";
import { createCaseApiStub } from "./stubs/case-api.js";

const request = {
  decision: "APPROVE" as const,
  action_digest: previewBundle.expected_sha256,
  case_revision: 1,
  policy_version: "demo-policy-v1",
  expires_at: previewBundle.decision_expires_at,
};

describe("required peer stubs", () => {
  it("case-api.v1 covers valid/unavailable/malformed/unauthorized", async () => {
    const valid = createCaseApiStub("valid");
    await expect(valid.decide("action-demo-1", request)).resolves.toMatchObject({
      decision: "APPROVE",
      reviewer_id: "supervisor-demo-1",
    });

    await expect(createCaseApiStub("unavailable").decide("action-demo-1", request)).rejects.toBeInstanceOf(
      DecisionClientError,
    );
    await expect(createCaseApiStub("malformed").decide("action-demo-1", request)).rejects.toMatchObject({
      uiCode: "MALFORMED",
    });
    await expect(
      createCaseApiStub("unauthorized_or_out_of_scope").decide("action-demo-1", request),
    ).rejects.toMatchObject({ uiCode: "UNAUTHORIZED" });
  });

  it("action-ledger.v1 covers valid/unavailable/malformed/unauthorized", async () => {
    const valid = createActionLedgerStub("valid");
    await expect(valid.decide("action-demo-1", request)).resolves.toMatchObject({
      action_digest: previewBundle.expected_sha256,
    });

    await expect(
      createActionLedgerStub("unavailable").getAction("action-demo-1"),
    ).rejects.toMatchObject({ uiCode: "UNAVAILABLE" });
    await expect(
      createActionLedgerStub("malformed").getAction("action-demo-1"),
    ).rejects.toMatchObject({ uiCode: "MALFORMED" });
    await expect(
      createActionLedgerStub("unauthorized_or_out_of_scope").decide(
        "action-demo-1",
        request,
      ),
    ).rejects.toMatchObject({ uiCode: "UNAUTHORIZED" });
  });
});
