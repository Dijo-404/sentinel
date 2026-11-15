/* Marketing simulator + guardrail models. Pure so the story the page tells is tested. */

export const STAGES = [
  { title: "Intake", sub: "Complaint + order bound" },
  { title: "Investigate", sub: "Evidence, masked refs" },
  { title: "Approve", sub: "One exact digest" },
  { title: "Dispatch", sub: "Single provider write" },
  { title: "Verify", sub: "Credit confirmed" },
] as const;

export const CHECKS = [
  { text: "Order bound to customer & tenant", code: "subject_scope" },
  { text: "Evidence fresh (< 72h)", code: "evidence.fresh" },
  { text: "Approval bound to payload digest", code: "sha256:9f2c…" },
  { text: "Reservation in one transaction", code: "txn.reserve" },
  { text: "Provider confirmed credit", code: "postcondition.ok" },
] as const;

export type Fault = "timeout" | "edited" | "double" | "stale";

export const FAULTS: Record<Fault, { title: string; detail: string; failsCheck: number; tag: string; outcome: string; body: string }> = {
  timeout: {
    title: "Provider timeout",
    detail: "Response never arrives",
    failsCheck: 3,
    tag: "RECONCILE · NOT RESEND",
    outcome: "Timeout → reconcile the original reference",
    body: "The dispatcher queries rfnd_••7Q2K again. No new refund ID is minted, and the reservation is not released because a lease expired.",
  },
  edited: {
    title: "Amount edited",
    detail: "₹4,250 → ₹42,500 after approval",
    failsCheck: 2,
    tag: "APPROVAL VOID",
    outcome: "Digest mismatch → approval rejected",
    body: "The approved digest covers 425000 minor units (₹4,250). The edited payload hashes differently, so the approval no longer applies.",
  },
  double: {
    title: "Duplicate click",
    detail: "Approve pressed twice",
    failsCheck: 2,
    tag: "IDEMPOTENT",
    outcome: "Second click → same operation",
    body: "The approval already holds a reservation and a stable operation reference. The duplicate returns the existing operation; nothing new is written.",
  },
  stale: {
    title: "Stale evidence",
    detail: "Capture record 9 days old",
    failsCheck: 1,
    tag: "BLOCKED AT GATE",
    outcome: "Stale evidence → proposal refused",
    body: "Policy requires evidence newer than 72 hours. The case returns to Investigate with a request for a fresh capture record.",
  },
};

export type SimState = { step: number; fault: Fault | null };

/** Advancing past a fault is impossible: a blocked case never reaches Verify. */
export function advance(s: SimState): SimState {
  if (s.fault) return s;
  return s.step >= STAGES.length ? { step: 0, fault: null } : { step: s.step + 1, fault: null };
}

export function inject(s: SimState, fault: Fault): SimState {
  if (s.fault === fault) return { ...s, fault: null };
  return { step: Math.max(s.step, FAULTS[fault].failsCheck + 1), fault };
}

export function checkStates(s: SimState) {
  return CHECKS.slice(0, Math.min(s.step, CHECKS.length)).map((c, i) => ({
    ...c,
    ok: !(s.fault && FAULTS[s.fault].failsCheck === i),
  }));
}

export const isResolved = (s: SimState) => s.step >= STAGES.length && s.fault === null;

export const ATTACKS = [
  { text: "Refund ₹42,500 instead of ₹4,250", blockedBy: 2 },
  { text: "Send money to a new bank account", blockedBy: 1 },
  { text: "Approve its own proposal", blockedBy: 0 },
  { text: "Retry with a fresh refund ID", blockedBy: 3 },
  { text: "Close the case on “pending”", blockedBy: 4 },
] as const;

export const LAYERS = [
  { title: "Authenticated identity", sub: "The server knows who is acting, not the prompt" },
  { title: "Original payment route", sub: "Refunds go back where the money came from" },
  { title: "Exact digest approval", sub: "A human approves one immutable payload" },
  { title: "Single dispatcher", sub: "One provider writer, one stable reference" },
  { title: "Verified postconditions", sub: "Provider confirmation before resolution" },
] as const;

/** Completed + pending + reserved + this refund must fit the daily cap. */
export function limitCheck(amount: number, used: number, cap: number) {
  const headroom = cap - used;
  return { allowed: amount <= headroom, headroom, after: headroom - amount, over: amount - headroom };
}
