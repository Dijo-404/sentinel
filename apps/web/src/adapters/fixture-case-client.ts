import type { CaseClient, CustomerCaseList } from "@/application/ports";
import {
  createCaseApiStub as createRawStub,
  demoAction,
  STUB_SCENARIOS,
  type CaseApiStubOptions,
  type StubCase,
} from "../../tests/stubs/case-api";

export { demoAction, STUB_SCENARIOS, type CaseApiStubOptions, type StubCase };

const FIXTURE_CUSTOMER_CASES: CustomerCaseList = {
  cases: [
    {
      case_id: "case-demo-42",
      status: "WAITING_APPROVAL",
      revision: 3,
      language: "en",
    },
  ],
};

/**
 * Fixture case client. Wraps the case-api stub with portal listCustomerCases
 * without editing tests/stubs/case-api (owned by the case-stub agent).
 */
export function createCaseApiStub(
  scenario: StubCase = "valid",
  options?: CaseApiStubOptions,
): CaseClient {
  const client = createRawStub(scenario, options);
  if (client.listCustomerCases) return client;

  if (scenario === "valid") {
    return {
      ...client,
      async listCustomerCases() {
        return {
          cases: FIXTURE_CUSTOMER_CASES.cases.map((c) => ({ ...c })),
        };
      },
    };
  }

  return {
    ...client,
    async listCustomerCases() {
      // Reuse an existing boom path on non-valid stubs.
      await client.getCase("case-demo-42");
      return { cases: [] };
    },
  };
}
