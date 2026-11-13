import type { DecideClient } from "../application/ports.js";
import type { Approval, DecisionRequest } from "../domain/types.js";
import { authorizedJson, type AuthorizedHttpConfig } from "./http.js";

/**
 * Real-peer adapter for case-api.v1:
 * POST /v1/ops/actions/{action_id}/decisions
 */
export function createCaseApiDecideClient(
  config: AuthorizedHttpConfig,
): DecideClient {
  return async (actionId: string, request: DecisionRequest): Promise<Approval> => {
    return authorizedJson<Approval>(
      config,
      "POST",
      `/v1/ops/actions/${encodeURIComponent(actionId)}/decisions`,
      request,
    );
  };
}
