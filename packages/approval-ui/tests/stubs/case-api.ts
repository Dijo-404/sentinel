import { DecisionClientError } from "../../src/domain/errors.js";
import type {
  Approval,
  DecisionRequest,
  Evidence,
  Principal,
  WireError,
} from "../../src/domain/types.js";
import previewBundle from "../../fixtures/preview-bundle.json";

export type StubCase =
  | "valid"
  | "unavailable"
  | "malformed"
  | "unauthorized_or_out_of_scope"
  | "expired"
  | "stale"
  | "cross_tenant"
  | "conflict";

export type CaseApiStub = {
  port: "case-api.v1";
  mode: "fixture";
  caseName: StubCase;
  decide: (actionId: string, request: DecisionRequest) => Promise<Approval>;
  getEvidence: (caseId: string) => Promise<Evidence[]>;
};

type Options = {
  principal?: Principal;
  approval?: Approval;
};

const defaultPrincipal = previewBundle.reviewer as Principal;
const defaultApproval = previewBundle.approval_response as Approval;
const defaultEvidence = previewBundle.evidence as Evidence[];

function error(code: string, message: string, requestId: string): WireError {
  return { code, message, request_id: requestId };
}

export function createCaseApiStub(
  caseName: StubCase,
  options: Options = {},
): CaseApiStub {
  const principal = options.principal ?? defaultPrincipal;
  const approval = options.approval ?? defaultApproval;

  return {
    port: "case-api.v1",
    mode: "fixture",
    caseName,
    async getEvidence(caseId: string): Promise<Evidence[]> {
      if (caseName === "unavailable") {
        throw new DecisionClientError(
          503,
          error("PEER_UNAVAILABLE", "Required peer unavailable", "case-api-unavail"),
          "UNAVAILABLE",
        );
      }
      if (caseName === "malformed") {
        throw new DecisionClientError(
          502,
          error("MALFORMED_RESPONSE", "Peer returned non-JSON body", "case-api-bad"),
          "MALFORMED",
        );
      }
      if (
        caseName === "unauthorized_or_out_of_scope" ||
        caseName === "cross_tenant" ||
        !principal.case_ids.includes(caseId)
      ) {
        throw new DecisionClientError(
          404,
          error("NOT_FOUND", "Resource not found", "case-api-scope"),
          caseName === "cross_tenant" ? "CROSS_TENANT" : "UNAUTHORIZED",
        );
      }
      return defaultEvidence;
    },
    async decide(actionId: string, request: DecisionRequest): Promise<Approval> {
      if (caseName === "unavailable") {
        throw new DecisionClientError(
          503,
          error("PEER_UNAVAILABLE", "Required peer unavailable", "case-api-unavail"),
          "UNAVAILABLE",
        );
      }
      if (caseName === "malformed") {
        throw new DecisionClientError(
          502,
          error("MALFORMED_RESPONSE", "Peer returned non-JSON body", "case-api-bad"),
          "MALFORMED",
        );
      }
      if (caseName === "unauthorized_or_out_of_scope") {
        throw new DecisionClientError(
          403,
          error("FORBIDDEN", "Resource not found", "case-api-unauth"),
          "UNAUTHORIZED",
        );
      }
      if (caseName === "cross_tenant") {
        throw new DecisionClientError(
          404,
          error("NOT_FOUND", "Resource not found", "case-api-tenant"),
          "CROSS_TENANT",
        );
      }
      if (caseName === "expired") {
        throw new DecisionClientError(
          409,
          error("APPROVAL_EXPIRED", "Approval window expired", "case-api-expired"),
          "EXPIRED",
        );
      }
      if (caseName === "stale") {
        throw new DecisionClientError(
          409,
          error("STALE_REVISION", "Case revision is stale", "case-api-stale"),
          "STALE",
        );
      }
      if (caseName === "conflict") {
        throw new DecisionClientError(
          409,
          error(
            "IDEMPOTENCY_CONFLICT",
            "Key already used with a different payload",
            "case-api-409",
          ),
          "CONFLICT",
        );
      }

      if (!principal.roles.includes("supervisor")) {
        throw new DecisionClientError(
          403,
          error("FORBIDDEN", "Resource not found", "case-api-role"),
          "UNAUTHORIZED",
        );
      }

      return {
        ...approval,
        approval_id: approval.approval_id,
        action_digest: request.action_digest,
        case_revision: request.case_revision,
        policy_version: request.policy_version,
        decision: request.decision,
        reviewer_id: principal.principal_id,
        expires_at: request.expires_at,
      };
    },
  };
}
