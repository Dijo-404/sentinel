import {
  PeerError,
  type ActionRecord,
  type Case,
  type CaseCreated,
  type EvidenceBundle,
  type OpsCaseList,
} from "@/domain/types";

function requireString(value: unknown, field: string, requestId: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", `Missing or invalid ${field}`, requestId);
  }
  return value;
}

function requireNumber(value: unknown, field: string, requestId: string): number {
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", `Missing or invalid ${field}`, requestId);
  }
  return value;
}

export function validateCase(value: unknown, requestId: string): Case {
  if (!value || typeof value !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Case is not an object", requestId);
  }
  const v = value as Record<string, unknown>;
  return {
    contract_version: requireString(
      v.contract_version,
      "contract_version",
      requestId,
    ) as Case["contract_version"],
    case_id: requireString(v.case_id, "case_id", requestId),
    revision: requireNumber(v.revision, "revision", requestId),
    status: requireString(v.status, "status", requestId) as Case["status"],
    language: requireString(v.language, "language", requestId),
    intent: requireString(v.intent, "intent", requestId),
    evidence_ids: Array.isArray(v.evidence_ids)
      ? (v.evidence_ids as string[])
      : (() => {
          throw new PeerError(
            "MALFORMED_PEER_RESPONSE",
            "Missing or invalid evidence_ids",
            requestId,
          );
        })(),
    ...(typeof v.action_id === "string" ? { action_id: v.action_id } : {}),
  };
}

export function validateCaseCreated(value: unknown, requestId: string): CaseCreated {
  if (!value || typeof value !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "CaseCreated is not an object", requestId);
  }
  const v = value as Record<string, unknown>;
  const status = requireString(v.status, "status", requestId);
  if (status !== "RECEIVED") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "CaseCreated.status must be RECEIVED",
      requestId,
    );
  }
  return {
    case_id: requireString(v.case_id, "case_id", requestId),
    status: "RECEIVED",
    status_url: requireString(v.status_url, "status_url", requestId),
  };
}

export function validateOpsList(value: unknown, requestId: string): OpsCaseList {
  if (!value || typeof value !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Ops list is not an object", requestId);
  }
  const v = value as Record<string, unknown>;
  if (!Array.isArray(v.cases)) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Missing or invalid cases", requestId);
  }
  return {
    cases: v.cases.map((c, i) => validateCase(c, `${requestId}-${i}`)),
    ...(typeof v.next_cursor === "string" ? { next_cursor: v.next_cursor } : {}),
  };
}

export function validateActionRecord(value: unknown, requestId: string): ActionRecord {
  if (!value || typeof value !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "ActionRecord is not an object", requestId);
  }
  const v = value as Record<string, unknown>;
  const payload = v.payload;
  if (!payload || typeof payload !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "ActionRecord.payload missing", requestId);
  }
  const p = payload as Record<string, unknown>;
  return {
    action_id: requireString(v.action_id, "action_id", requestId),
    provider_ref: requireString(v.provider_ref, "provider_ref", requestId),
    action_digest: requireString(v.action_digest, "action_digest", requestId),
    status: requireString(v.status, "status", requestId) as ActionRecord["status"],
    payload: {
      action: "REQUEST_REFUND",
      case_id: requireString(p.case_id, "payload.case_id", requestId),
      case_revision: requireNumber(p.case_revision, "payload.case_revision", requestId),
      evidence_ids: Array.isArray(p.evidence_ids)
        ? (p.evidence_ids as string[])
        : (() => {
            throw new PeerError(
              "MALFORMED_PEER_RESPONSE",
              "Missing or invalid payload.evidence_ids",
              requestId,
            );
          })(),
      policy_version: requireString(p.policy_version, "payload.policy_version", requestId),
      transaction_ref: requireString(p.transaction_ref, "payload.transaction_ref", requestId),
      amount_minor: requireNumber(p.amount_minor, "payload.amount_minor", requestId),
      currency: "INR",
      destination: "ORIGINAL_PAYMENT_ROUTE",
    },
    ...(v.approval && typeof v.approval === "object"
      ? { approval: v.approval as ActionRecord["approval"] }
      : {}),
  };
}

export function validateEvidenceBundle(value: unknown, requestId: string): EvidenceBundle {
  if (!value || typeof value !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Evidence bundle is not an object", requestId);
  }
  const v = value as Record<string, unknown>;
  if (!Array.isArray(v.evidence)) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Missing or invalid evidence", requestId);
  }
  return {
    contract_version: requireString(
      v.contract_version,
      "contract_version",
      requestId,
    ) as EvidenceBundle["contract_version"],
    case_id: requireString(v.case_id, "case_id", requestId),
    evidence: v.evidence as EvidenceBundle["evidence"],
    reconciliation_codes: Array.isArray(v.reconciliation_codes)
      ? (v.reconciliation_codes as string[])
      : [],
  };
}
