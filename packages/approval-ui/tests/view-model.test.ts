import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  buildApprovalViewModel,
  buildDecisionRequest,
} from "../src/domain/view-model.js";
import type { ActionRecord, Case, Evidence } from "../src/domain/types.js";
import previewBundle from "../fixtures/preview-bundle.json";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

describe("approval view model", () => {
  const now = new Date(previewBundle.virtual_now);

  it("exposes amount, transaction, policy, ages, digest, expiry, reviewer", () => {
    const view = buildApprovalViewModel(
      {
        case: previewBundle.case as Case,
        action: previewBundle.action as ActionRecord,
        evidence: previewBundle.evidence as Evidence[],
      },
      previewBundle.reviewer.principal_id,
      previewBundle.decision_expires_at,
      now,
    );

    expect(view.amount_minor).toBe(150000);
    expect(view.transaction_ref).toBe("TXN-B");
    expect(view.policy_version).toBe("demo-policy-v1");
    expect(view.action_digest).toBe(previewBundle.expected_sha256);
    expect(view.decision_expires_at).toBe("2026-11-13T14:00:00Z");
    expect(view.reviewer_id).toBe("supervisor-demo-1");
    expect(view.evidence_ages).toEqual([
      {
        evidence_id: "evidence-payment-b",
        observed_at: "2026-11-13T11:00:00Z",
        expires_at: "2026-11-13T18:00:00Z",
        age_seconds: 3600,
        expired: false,
      },
      {
        evidence_id: "evidence-order",
        observed_at: "2026-11-13T11:05:00Z",
        expires_at: "2026-11-13T18:00:00Z",
        age_seconds: 3300,
        expired: false,
      },
    ]);
  });

  it("matches canonical digest bytes from the pinned fixture", () => {
    const digest = createHash("sha256")
      .update(previewBundle.canonical_action_utf8, "utf8")
      .digest("hex");
    expect(digest).toBe(previewBundle.expected_sha256);
    expect(previewBundle.action.action_digest).toBe(digest);
  });

  it("builds decision requests from supplied digest and revision only", () => {
    const request = buildDecisionRequest(
      previewBundle.expected_sha256,
      1,
      "demo-policy-v1",
      previewBundle.decision_expires_at,
      "APPROVE",
    );
    expect(request).toEqual({
      decision: "APPROVE",
      action_digest: previewBundle.expected_sha256,
      case_revision: 1,
      policy_version: "demo-policy-v1",
      expires_at: "2026-11-13T14:00:00Z",
    });
  });

  it("pins the contract baseline hash file", () => {
    const hash = readFileSync(join(root, "contracts/baseline-hash.txt"), "utf8").trim();
    expect(hash).toBe(
      "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa",
    );
  });
});
