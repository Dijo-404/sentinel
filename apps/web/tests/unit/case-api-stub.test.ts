import { describe, expect, it } from "vitest";
import { createCaseApiStub } from "../stubs/case-api";
import { PeerError } from "@/domain/types";

const demoDigest = "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993";

const decideBody = {
  decision: "APPROVE" as const,
  action_digest: demoDigest,
  case_revision: 2,
  policy_version: "demo-policy-v1",
  expires_at: "2026-12-31T23:59:59Z",
};

describe("createCaseApiStub valid client", () => {
  it("decide rejects non-supervisor with FORBIDDEN", async () => {
    const denied = createCaseApiStub("valid");
    await expect(denied.decide("action-demo-1", decideBody)).rejects.toMatchObject({
      code: "FORBIDDEN",
      httpStatus: 403,
    });
    await expect(
      createCaseApiStub("valid", { reviewerRole: "operator" }).decide("action-demo-1", decideBody),
    ).rejects.toBeInstanceOf(PeerError);

    const allowed = createCaseApiStub("valid", {
      reviewerRole: "supervisor",
    });
    const approval = await allowed.decide("action-demo-1", decideBody);
    expect(approval.decision).toBe("APPROVE");
    expect(approval.approval_id).toBe("approval-demo-1");
  });

  it("createCase rejects blank or whitespace-only order_reference", async () => {
    const client = createCaseApiStub("valid");
    const base = {
      message: "paid twice",
      language: "en-IN",
      channel: "web" as const,
    };
    for (const order_reference of ["", "   ", "\t"]) {
      await expect(
        client.createCase({ ...base, order_reference }, "idem-blank"),
      ).rejects.toMatchObject({
        code: "INVALID_INPUT",
        httpStatus: 422,
      });
    }
  });

  it("createCase mint unique ids and getCase serves fixture plus created", async () => {
    const client = createCaseApiStub("valid");
    const fixture = await client.getCase("case-demo-42");
    expect(fixture.case_id).toBe("case-demo-42");
    expect(fixture.status).toBe("WAITING_APPROVAL");

    const a = await client.createCase(
      {
        message: "first",
        language: "en-IN",
        order_reference: "ORD-A",
        channel: "web",
      },
      "idem-a",
    );
    const b = await client.createCase(
      {
        message: "second",
        language: "en-IN",
        order_reference: "ORD-B",
        channel: "web",
      },
      "idem-b",
    );
    expect(a.case_id).toMatch(/^case-demo-\d+$/);
    expect(b.case_id).toMatch(/^case-demo-\d+$/);
    expect(a.case_id).not.toBe("case-demo-42");
    expect(b.case_id).not.toBe(a.case_id);

    const loaded = await client.getCase(a.case_id);
    expect(loaded.status).toBe("RECEIVED");
    expect(loaded.revision).toBe(1);
    expect(await client.getCase("case-demo-42")).toMatchObject({
      case_id: "case-demo-42",
      status: "WAITING_APPROVAL",
    });
  });

  it("postMessage and escalate append timeline events and persist status", async () => {
    const client = createCaseApiStub("valid");
    const before = await client.listEvents("case-demo-42");
    expect(before.events.map((e) => e.type)).toEqual(["CASE_CREATED", "STATUS_CHANGED"]);

    const afterMsg = await client.postMessage("case-demo-42", {
      message: "need more info",
      language: "en-IN",
      expected_revision: 2,
    });
    expect(afterMsg.status).toBe("NEEDS_INPUT");
    expect(afterMsg.revision).toBe(3);

    const mid = await client.getCase("case-demo-42");
    expect(mid.status).toBe("NEEDS_INPUT");
    expect(mid.revision).toBe(3);

    const afterEsc = await client.escalate("case-demo-42", {
      reason_code: "STUCK",
      owner_queue: "SUPERVISOR",
      expected_revision: 3,
    });
    expect(afterEsc.status).toBe("ESCALATED");
    await expect(
      client.escalate("case-demo-42", {
        reason_code: "STUCK",
        // Lower-case queue is what case-api rejected in the deployed sandbox.
        owner_queue: "supervisor" as never,
        expected_revision: 4,
      }),
    ).rejects.toMatchObject({ code: "INVALID_INPUT" });
    expect(afterEsc.revision).toBe(4);

    const persisted = await client.getCase("case-demo-42");
    expect(persisted.status).toBe("ESCALATED");
    expect(persisted.revision).toBe(4);

    const events = await client.listEvents("case-demo-42");
    const types = events.events.map((e) => e.type);
    expect(types).toContain("MESSAGE_ADDED");
    expect(types).toContain("ESCALATED");
    expect(events.events.find((e) => e.type === "MESSAGE_ADDED")?.case_revision).toBe(3);
    expect(events.events.find((e) => e.type === "ESCALATED")?.case_revision).toBe(4);
  });

  it("listOpsMessages and listOpsAuditEvents return seeded fixture shapes", async () => {
    const client = createCaseApiStub("valid");
    const messages = await client.listOpsMessages();
    expect(messages.messages.length).toBeGreaterThanOrEqual(1);
    expect(messages.messages[0]).toMatchObject({
      case_id: expect.any(String),
      message_id: expect.any(String),
      text: expect.any(String),
      language: expect.any(String),
      author: expect.any(String),
      occurred_at: expect.any(String),
    });

    const audit = await client.listOpsAuditEvents();
    expect(audit.events.length).toBeGreaterThanOrEqual(1);
    expect(audit.events[0]).toMatchObject({
      case_id: expect.any(String),
      sequence: expect.any(Number),
      type: expect.any(String),
      occurred_at: expect.any(String),
      payload: expect.any(Object),
    });
  });

  it("listOpsCases status=HISTORY returns only terminal history statuses", async () => {
    const client = createCaseApiStub("valid");
    const history = await client.listOpsCases({ status: "HISTORY" });
    expect(history.cases.length).toBeGreaterThanOrEqual(1);
    for (const row of history.cases) {
      expect(["VERIFIED_RESOLVED", "CLOSED_NO_ACTION"]).toContain(row.status);
    }
  });
});
