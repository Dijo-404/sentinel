import { describe, expect, it, vi } from "vitest";
import { createRealPeerMerchantAnalyticsClient } from "@/adapters/real-peer-merchant-analytics-client";
import { createRealPeerRiskClient } from "@/adapters/real-peer-risk-client";
import { createRealPeerCaseClient } from "@/adapters/real-peer-case-client";
import { FIXTURE_MERCHANT_METRICS } from "./stubs/merchant-analytics";
import { FIXTURE_RISK_DASHBOARD } from "./stubs/risk";
import { PeerError } from "@/domain/types";

describe("peer clients", () => {
  it("listCustomerCases calls GET /v1/customer/cases", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          cases: [
            {
              case_id: "case-1",
              status: "RECEIVED",
              revision: 1,
              language: "en",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    const client = createRealPeerCaseClient({
      baseUrl: "http://case.test",
      bearerToken: "tok",
      fetchImpl: fetchImpl as typeof fetch,
    });
    const result = await client.listCustomerCases!();
    expect(result.cases).toHaveLength(1);
    expect(String(fetchImpl.mock.calls[0]![0])).toContain(
      "/v1/customer/cases",
    );
  });

  it("merchant analytics client GETs metrics path", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(FIXTURE_MERCHANT_METRICS), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const client = createRealPeerMerchantAnalyticsClient({
      baseUrl: "http://ma.test",
      bearerToken: "tok",
      fetchImpl: fetchImpl as typeof fetch,
    });
    const metrics = await client.getMetrics("merchant-demo-1", {
      window_start: FIXTURE_MERCHANT_METRICS.window_start,
      window_end: FIXTURE_MERCHANT_METRICS.window_end,
    });
    expect(metrics.unresolved_minor).toBe(100000);
    expect(String(fetchImpl.mock.calls[0]![0])).toContain(
      "/v1/merchants/merchant-demo-1/metrics",
    );
  });

  it("risk client GETs /v1/risk/dashboard", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(FIXTURE_RISK_DASHBOARD), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const client = createRealPeerRiskClient({
      baseUrl: "http://risk.test",
      bearerToken: "tok",
      fetchImpl: fetchImpl as typeof fetch,
    });
    const dash = await client.getDashboard();
    expect(dash.open_investigations).toBe(1);
    expect(String(fetchImpl.mock.calls[0]![0])).toContain("/v1/risk/dashboard");
  });

  it("risk client GETs portal list paths", async () => {
    const fetchImpl = vi.fn().mockImplementation((url: string) => {
      const path = String(url);
      let body: unknown = {};
      if (path.includes("/investigations")) {
        body = {
          investigations: [
            {
              investigation_id: "inv-1",
              case_id: "case-1",
              status: "OPEN",
              reason_code: "R",
              queue_ref: "FRAUD",
              severity: "HIGH",
              updated_at: "2026-11-15T00:00:00Z",
            },
          ],
        };
      } else if (path.includes("/restrictions")) {
        body = {
          restrictions: [
            {
              restriction_id: "rst-1",
              case_id: "case-1",
              investigation_id: "inv-1",
              status: "ACTIVE",
              reason_code: "R",
              blocks_financial_actions: true,
              transaction_ref: "TXN-B",
              financial_approval_granted: false,
            },
          ],
        };
      } else if (path.includes("/findings")) {
        body = {
          findings: [
            {
              finding_id: "fnd-1",
              investigation_id: "inv-1",
              classification: "SUSPICIOUS",
              notes: "n",
              recorded_at: "2026-11-15T00:00:00Z",
            },
          ],
        };
      } else if (path.includes("/reports")) {
        body = { ...FIXTURE_RISK_DASHBOARD, report_kind: "summary" };
      }
      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    });
    const client = createRealPeerRiskClient({
      baseUrl: "http://risk.test",
      bearerToken: "tok",
      fetchImpl: fetchImpl as typeof fetch,
    });
    expect((await client.listInvestigations()).investigations).toHaveLength(1);
    expect(
      (
        await client.listRestrictions({ blocks_financial_actions: true })
      ).restrictions[0]?.blocks_financial_actions,
    ).toBe(true);
    expect(String(fetchImpl.mock.calls[1]![0])).toContain(
      "blocks_financial_actions=true",
    );
    expect((await client.listFindings()).findings[0]?.finding_id).toBe("fnd-1");
    expect((await client.getReports()).report_kind).toBe("summary");
  });

  it("merchant analytics network failure stays PeerError", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error("ECONNREFUSED"));
    const client = createRealPeerMerchantAnalyticsClient({
      baseUrl: "http://ma.test",
      bearerToken: "tok",
      fetchImpl: fetchImpl as typeof fetch,
    });
    await expect(
      client.getMetrics("m1", {
        window_start: "2026-11-01T00:00:00Z",
        window_end: "2026-11-14T00:00:00Z",
      }),
    ).rejects.toBeInstanceOf(PeerError);
  });
});
