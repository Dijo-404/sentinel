export { ApprovalPanel } from "./ui/ApprovalPanel.js";
export type { ApprovalPanelProps } from "./ui/ApprovalPanel.js";

export { buildApprovalViewModel, buildDecisionRequest } from "./domain/view-model.js";
export { submitDecision } from "./application/submit-decision.js";
export type { DecideClient, Clock } from "./application/ports.js";

export { createCaseApiDecideClient } from "./adapters/case-api-client.js";
export { createActionLedgerDecideClient } from "./adapters/action-ledger-client.js";
export { DecisionClientError, accessibleMessage, mapWireError } from "./domain/errors.js";

export type {
  Approval,
  ApprovalUiInput,
  ApprovalViewModel,
  ActionRecord,
  Case,
  ConflictEvent,
  Decision,
  DecisionRequest,
  DecisionOutcome,
  DecisionUiCode,
  Evidence,
  RefreshEvent,
  WireError,
} from "./domain/types.js";

export { CONTRACT_VERSION } from "./domain/types.js";
