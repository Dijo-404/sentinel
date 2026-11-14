import { describe, expect, it } from "vitest";
import { buildCapabilities } from "@/domain/capabilities";
import { CONTRACT_VERSION } from "@/domain/types";
import { GET } from "@/app/v1/capabilities/route";
import { loadShellConfig } from "@/adapters/composition";

describe("GET /v1/capabilities", () => {
  it("builds assembly probe payload", () => {
    expect(buildCapabilities("fixture")).toEqual({
      contract_version: CONTRACT_VERSION,
      component: "web-shell",
      port: "web-shell.v1",
      mode: "fixture",
    });
    expect(buildCapabilities("real-peers")).toMatchObject({
      mode: "real-peers",
      port: "web-shell.v1",
      component: "web-shell",
    });
  });

  it("route handler returns JSON from SHELL_MODE env", async () => {
    const prev = process.env.NEXT_PUBLIC_SHELL_MODE;
    process.env.NEXT_PUBLIC_SHELL_MODE = "fixture";
    try {
      const res = GET();
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body).toEqual({
        contract_version: loadShellConfig().contractVersion,
        component: "web-shell",
        port: "web-shell.v1",
        mode: "fixture",
      });
    } finally {
      if (prev === undefined) {
        delete process.env.NEXT_PUBLIC_SHELL_MODE;
      } else {
        process.env.NEXT_PUBLIC_SHELL_MODE = prev;
      }
    }
  });

  it("reflects real-peers mode from env", async () => {
    const prev = process.env.NEXT_PUBLIC_SHELL_MODE;
    process.env.NEXT_PUBLIC_SHELL_MODE = "real-peers";
    try {
      const body = await GET().json();
      expect(body.mode).toBe("real-peers");
      expect(body.component).toBe("web-shell");
      expect(body.port).toBe("web-shell.v1");
    } finally {
      if (prev === undefined) {
        delete process.env.NEXT_PUBLIC_SHELL_MODE;
      } else {
        process.env.NEXT_PUBLIC_SHELL_MODE = prev;
      }
    }
  });
});
