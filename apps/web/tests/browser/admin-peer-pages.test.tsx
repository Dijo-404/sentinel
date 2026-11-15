import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { AdminPeerPanel, type AdminPeerView } from "@/components/admin/admin-peer-panel";

/** One representative page per peer family (+ peer-error). */
const PEER_FAMILY_PAGES: {
  view: AdminPeerView;
  peer: string;
  okBody: unknown;
  okBodies?: Record<string, unknown>;
}[] = [
  {
    view: "roles",
    peer: "identity",
    okBody: {
      human_roles: ["platform_admin", "operator"],
      staff_invitable_roles: ["operator"],
      service_roles: ["workflow"],
    },
  },
  {
    view: "policies",
    peer: "policy",
    okBody: {
      policies: [
        {
          policy_id: "demo-policy-v1",
          version: "demo-policy-v1",
          status: "active",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
    },
  },
  {
    view: "merchants",
    peer: "merchant-teams",
    okBody: {
      merchants: [
        {
          merchant_ref: "merchant-demo-1",
          display_name: "Demo Merchant",
          status: "active",
        },
      ],
    },
  },
  {
    view: "integrations",
    peer: "platform-ai",
    okBody: {
      integrations: [
        {
          integration_id: "integration-sandbox-1",
          name: "Sandbox webhook",
          status: "ACTIVE",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
    },
  },
  {
    view: "ai",
    peer: "platform-ai",
    okBody: {},
    okBodies: {
      "/api/bff/platform-ai/v1/config": {
        models: [{ model_id: "model-sandbox-1" }],
        kill_switch: false,
        updated_at: "2026-01-01T00:00:00Z",
      },
      "/api/bff/platform-ai/v1/runs": {
        runs: [
          {
            run_id: "run-demo-1",
            model_id: "model-sandbox-1",
            status: "SUCCEEDED",
            started_at: "2026-01-01T00:00:00Z",
          },
        ],
      },
    },
  },
  {
    view: "evaluations",
    peer: "evals",
    okBody: {
      reports: [
        {
          run_id: "run-seed-1",
          status: "PASS",
          mode: "fixture",
          contract_version: "evaluation.v1",
        },
      ],
    },
  },
  {
    view: "observability",
    peer: "observability",
    okBody: {
      signals: [
        {
          signal_id: "sig-1",
          kind: "span",
          name: "demo.span",
          recorded_at: "2026-01-01T00:00:00Z",
        },
      ],
      financial_audit: false,
    },
  },
];

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const FIN_GATES = {
  finharness: "gated_disabled",
  finbench: "gated_disabled",
  live_stats: null,
  notes: ["test"],
};

function fetchOkFor(entry: (typeof PEER_FAMILY_PAGES)[number]): typeof fetch {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/bff/admin-fin-gates") || url.includes("admin-fin-gates")) {
      return jsonResponse(FIN_GATES);
    }
    if (entry.okBodies) {
      for (const [path, body] of Object.entries(entry.okBodies)) {
        if (url.includes(path) || url.endsWith(path.replace(/^https?:\/\/[^/]+/, ""))) {
          return jsonResponse(body);
        }
        if (url.includes(path.split("/").slice(-2).join("/"))) {
          return jsonResponse(body);
        }
      }
      // Match by trailing peer path segments
      if (url.includes("/v1/config")) {
        return jsonResponse(entry.okBodies["/api/bff/platform-ai/v1/config"]);
      }
      if (url.includes("/v1/runs")) {
        return jsonResponse(entry.okBodies["/api/bff/platform-ai/v1/runs"]);
      }
    }
    return jsonResponse(entry.okBody);
  }) as unknown as typeof fetch;
}

function fetchFail(): typeof fetch {
  return vi.fn(async () => {
    throw new TypeError("fetch failed");
  }) as unknown as typeof fetch;
}

describe("admin peer pages", () => {
  it.each(PEER_FAMILY_PAGES)(
    "$view ($peer) never shows stub copy; data when fetch succeeds",
    async (entry) => {
      render(
        <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "real-peers" })}>
          <AdminPeerPanel view={entry.view} fetchImpl={fetchOkFor(entry)} />
        </ShellProvider>,
      );

      expect(screen.getByTestId(`admin-${entry.view}`)).toBeInTheDocument();
      expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
      expect(await screen.findByTestId(`admin-${entry.view}-data`)).toBeInTheDocument();
      expect(screen.queryByTestId("peer-error")).not.toBeInTheDocument();
    },
  );

  it.each(PEER_FAMILY_PAGES)(
    "$view ($peer) peer failure shows peer-error — no stub copy",
    async (entry) => {
      render(
        <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "real-peers" })}>
          <AdminPeerPanel view={entry.view} fetchImpl={fetchFail()} />
        </ShellProvider>,
      );

      expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
      expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
      expect(screen.queryByTestId(`admin-${entry.view}-data`)).not.toBeInTheDocument();
    },
  );

  it("tenants / teams / security / audit keep admin-* testids without stub copy", async () => {
    const bodies: Record<string, unknown> = {
      tenants: {
        tenants: [
          {
            tenant_id: "tenant-demo",
            display_name: "Demo",
            status: "active",
          },
        ],
      },
      teams: {
        teams: [{ team_id: "payments-support", name: "Payments", member_count: 2 }],
      },
      security: {
        mfa_verified_sessions: 1,
        active_sessions: 2,
        suspended_users: 0,
        updated_at: "2026-01-01T00:00:00Z",
      },
      audit: {
        events: [
          {
            event_id: "evt-1",
            action: "login",
            target_type: "user",
            target_id: "u-1",
            at: "2026-01-01T00:00:00Z",
          },
        ],
      },
    };

    for (const view of ["tenants", "teams", "security", "audit"] as const) {
      const fetchImpl = vi.fn(async () => jsonResponse(bodies[view])) as unknown as typeof fetch;
      const { unmount } = render(
        <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "real-peers" })}>
          <AdminPeerPanel view={view} fetchImpl={fetchImpl} />
        </ShellProvider>,
      );
      expect(await screen.findByTestId(`admin-${view}-data`)).toBeInTheDocument();
      expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
      unmount();
    }
  });
});
