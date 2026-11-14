/**
 * Optional peer clients for merchant/risk/settlement/teams.
 * Kept out of composition.ts so case-stub agents can edit that file safely.
 */
import type {
  MerchantAnalyticsClient,
  MerchantDisputesClient,
  MerchantInboxClient,
  MerchantSettlementClient,
  MerchantTeamsClient,
  RiskClient,
  ShellMode,
} from "@/application/ports";
import { createBffMerchantAnalyticsClient } from "./real-peer-merchant-analytics-client";
import { createBffMerchantDisputesClient } from "./real-peer-merchant-disputes-client";
import { createBffMerchantInboxClient } from "./real-peer-merchant-inbox-client";
import { createBffMerchantSettlementClient } from "./real-peer-merchant-settlement-client";
import { createBffMerchantTeamsClient } from "./real-peer-merchant-teams-client";
import { createBffRiskClient } from "./real-peer-risk-client";
import { createMerchantAnalyticsStub } from "../../tests/stubs/merchant-analytics";
import { createMerchantDisputesStub } from "../../tests/stubs/merchant-disputes";
import { createMerchantInboxStub } from "../../tests/stubs/merchant-inbox";
import { createMerchantSettlementStub } from "../../tests/stubs/merchant-settlement";
import { createMerchantTeamsStub } from "../../tests/stubs/merchant-teams";
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

export function createMerchantTeamsClientForMode(
  mode: ShellMode,
  overrides?: {
    client?: MerchantTeamsClient;
    fetchImpl?: typeof fetch;
  },
): MerchantTeamsClient {
  if (overrides?.client) return overrides.client;
  if (mode === "fixture") return createMerchantTeamsStub("valid");
  return createBffMerchantTeamsClient({
    fetchImpl: overrides?.fetchImpl,
  });
}

export function createMerchantDisputesClientForMode(
  mode: ShellMode,
  overrides?: {
    client?: MerchantDisputesClient;
    fetchImpl?: typeof fetch;
  },
): MerchantDisputesClient {
  if (overrides?.client) return overrides.client;
  if (mode === "fixture") return createMerchantDisputesStub("valid");
  return createBffMerchantDisputesClient({ fetchImpl: overrides?.fetchImpl });
}

export function createMerchantInboxClientForMode(
  mode: ShellMode,
  overrides?: {
    client?: MerchantInboxClient;
    fetchImpl?: typeof fetch;
  },
): MerchantInboxClient {
  if (overrides?.client) return overrides.client;
  if (mode === "fixture") return createMerchantInboxStub("valid");
  return createBffMerchantInboxClient({ fetchImpl: overrides?.fetchImpl });
}
