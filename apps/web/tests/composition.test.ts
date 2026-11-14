import { describe, expect, it } from "vitest";
import { createShellRuntime, loadShellConfig } from "@/adapters/composition";
import { PeerError } from "@/domain/types";

describe("loadShellConfig bearer policy", () => {
  it("fixture may use NEXT_PUBLIC_DEMO_TOKEN", () => {
    const config = loadShellConfig({
      NEXT_PUBLIC_SHELL_MODE: "fixture",
      NEXT_PUBLIC_DEMO_TOKEN: "tok-public",
    });
    expect(config.bearerToken).toBe("tok-public");
  });

  it("real-peers does not embed process-wide CASE_API_BEARER_TOKEN in shell config", () => {
    const config = loadShellConfig({
      NEXT_PUBLIC_SHELL_MODE: "real-peers",
      CASE_API_BASE_URL: "http://127.0.0.1:8080",
      CASE_API_BEARER_TOKEN: "tok-server",
      NEXT_PUBLIC_DEMO_TOKEN: "tok-public",
    });
    expect(config.bearerToken).toBeUndefined();
    expect(config.caseApiBaseUrl).toBe("http://127.0.0.1:8080");
  });

  it("real-peers refuses NEXT_PUBLIC_DEMO_TOKEN without CASE_API_BASE_URL", () => {
    let caught: unknown;
    try {
      loadShellConfig({
        NEXT_PUBLIC_SHELL_MODE: "real-peers",
        NEXT_PUBLIC_DEMO_TOKEN: "tok-public",
      });
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(PeerError);
    expect((caught as PeerError).code).toBe("INVALID_CONFIG");
    expect((caught as PeerError).message).toMatch(/CASE_API_BASE_URL/);
    expect((caught as PeerError).message).toMatch(/NEXT_PUBLIC_/);
  });

  it("real-peers shell runtime uses BFF client (no shared bearer)", () => {
    const runtime = createShellRuntime(
      loadShellConfig({
        NEXT_PUBLIC_SHELL_MODE: "real-peers",
        CASE_API_BASE_URL: "http://127.0.0.1:8080",
      }),
    );
    expect(runtime.config.bearerToken).toBeUndefined();
    expect(runtime.config.mode).toBe("real-peers");
  });
});
