import type { Approval, DecisionRequest } from "../domain/types.js";

/**
 * Injected authorized client. Models never approve: the host supplies a
 * supervisor-authenticated adapter that posts DecisionRequest to case-api or ledger.
 */
export type DecideClient = (actionId: string, request: DecisionRequest) => Promise<Approval>;

export type Clock = () => Date;
