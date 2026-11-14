/**
 * Optional peer clients for merchant/risk/settlement.
 * Kept out of composition.ts so case-stub agents can edit that file safely.
 */
import type {
  MerchantAnalyticsClient,
  MerchantSettlementClient,
  RiskClient,
  ShellMode,
} from "@/application/ports";
import { createBffMerchantAnalyticsClient } from "./real-peer-merchant-analytics-client";
import { createBffMerchantSettlementClient } from "./real-peer-merchant-settlement-client";
import { createBffRiskClient } from "./real-peer-risk-client";
import { createMerchantAnalyticsStub } from "../../tests/stubs/merchant-analytics";
import { createMerchantSettlementStub } from "../../tests/stubs/merchant-settlement";
import { createRiskStub } from "../../tests/stubs/risk";

export function createMerchantAnalyticsClientForMode(
  mode: ShellMode,
  overrides?: { client?: MerchantAnalyticsClient; fetchImpl?: typeof fetch },
): MerchantAnalyticsClient {
  if (overrides?.client) return overrides.client;
  if (mode === "fixture") return createMerchantAnalyticsStub("valid");
  return createBffMerchantAnalyticsClient({ fetchImpl: overrides?.fetchImpl });
}

export function createRiskClientForMode(
  mode: ShellMode,
  overrides?: { client?: RiskClient; fetchImpl?: typeof fetch },
): RiskClient {
  if (overrides?.client) return overrides.client;
  if (mode === "fixture") return createRiskStub("valid");
  return createBffRiskClient({ fetchImpl: overrides?.fetchImpl });
}

export function createMerchantSettlementClientForMode(
  mode: ShellMode,
  overrides?: {
    client?: MerchantSettlementClient;
    fetchImpl?: typeof fetch;
  },
): MerchantSettlementClient {
  if (overrides?.client) return overrides.client;
  if (mode === "fixture") return createMerchantSettlementStub("valid");
  return createBffMerchantSettlementClient({
    fetchImpl: overrides?.fetchImpl,
  });
}
