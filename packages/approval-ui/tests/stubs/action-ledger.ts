import { DecisionClientError } from "../../src/domain/errors.js";
import type {
  ActionRecord,
  Approval,
  DecisionRequest,
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

export type ActionLedgerStub = {
  port: "action-ledger.v1";
  mode: "fixture";
  caseName: StubCase;
  decide: (actionId: string, request: DecisionRequest) => Promise<Approval>;
  getAction: (actionId: string) => Promise<ActionRecord>;
};

type Options = {
  principal?: Principal;
  approval?: Approval;
  action?: ActionRecord;
};

const defaultPrincipal = previewBundle.reviewer as Principal;
const defaultApproval = previewBundle.approval_response as Approval;
const defaultAction = previewBundle.action as ActionRecord;

function error(code: string, message: string, requestId: string): WireError {
  return { code, message, request_id: requestId };
}

export function createActionLedgerStub(
  caseName: StubCase,
  options: Options = {},
): ActionLedgerStub {
  const principal = options.principal ?? defaultPrincipal;
  const approval = options.approval ?? defaultApproval;
  const action = options.action ?? defaultAction;

  return {
    port: "action-ledger.v1",
    mode: "fixture",
    caseName,
    async getAction(actionId: string): Promise<ActionRecord> {
      if (caseName === "unavailable") {
        throw new DecisionClientError(
          503,
          error("PEER_UNAVAILABLE", "Required peer unavailable", "ledger-unavail"),
          "UNAVAILABLE",
        );
      }
      if (caseName === "malformed") {
        throw new DecisionClientError(
          502,
          error("MALFORMED_RESPONSE", "Peer returned non-JSON body", "ledger-bad"),
          "MALFORMED",
        );
      }
      if (
        caseName === "unauthorized_or_out_of_scope" ||
        caseName === "cross_tenant" ||
        actionId !== action.action_id
      ) {
        throw new DecisionClientError(
          404,
          error("NOT_FOUND", "Resource not found", "ledger-scope"),
          caseName === "cross_tenant" ? "CROSS_TENANT" : "UNAUTHORIZED",
        );
      }
      return action;
    },
    async decide(actionId: string, request: DecisionRequest): Promise<Approval> {
      if (caseName === "unavailable") {
        throw new DecisionClientError(
          503,
          error("PEER_UNAVAILABLE", "Required peer unavailable", "ledger-unavail"),
          "UNAVAILABLE",
        );
      }
      if (caseName === "malformed") {
        throw new DecisionClientError(
          502,
          error("MALFORMED_RESPONSE", "Peer returned non-JSON body", "ledger-bad"),
          "MALFORMED",
        );
      }
      if (caseName === "unauthorized_or_out_of_scope") {
        throw new DecisionClientError(
          403,
          error("FORBIDDEN", "Resource not found", "ledger-unauth"),
          "UNAUTHORIZED",
        );
      }
      if (caseName === "cross_tenant") {
        throw new DecisionClientError(
          404,
          error("NOT_FOUND", "Resource not found", "ledger-tenant"),
          "CROSS_TENANT",
        );
      }
      if (caseName === "expired") {
        throw new DecisionClientError(
          409,
          error("APPROVAL_EXPIRED", "Approval window expired", "ledger-expired"),
          "EXPIRED",
        );
      }
      if (caseName === "stale") {
        throw new DecisionClientError(
          409,
          error("STALE_REVISION", "Case revision is stale", "ledger-stale"),
          "STALE",
        );
      }
      if (caseName === "conflict") {
        throw new DecisionClientError(
          409,
          error("IDEMPOTENCY_CONFLICT", "Key already used with a different payload", "ledger-409"),
          "CONFLICT",
        );
      }

      if (actionId !== action.action_id) {
        throw new DecisionClientError(
          404,
          error("NOT_FOUND", "Resource not found", "ledger-missing"),
          "UNAUTHORIZED",
        );
      }
      if (request.action_digest !== action.action_digest) {
        throw new DecisionClientError(
          409,
          error("DIGEST_CONFLICT", "Action digest mismatch", "ledger-digest"),
          "CONFLICT",
        );
      }
      if (!principal.roles.includes("supervisor")) {
        throw new DecisionClientError(
          403,
          error("FORBIDDEN", "Resource not found", "ledger-role"),
          "UNAUTHORIZED",
        );
      }

      return {
        ...approval,
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
