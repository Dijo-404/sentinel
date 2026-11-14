import { describe, expect, it } from "vitest";
import { loadShellConfig } from "@/adapters/composition";
import { PeerError } from "@/domain/types";

describe("loadShellConfig bearer policy", () => {
  it("fixture may use NEXT_PUBLIC_DEMO_TOKEN", () => {
    const config = loadShellConfig({
      NEXT_PUBLIC_SHELL_MODE: "fixture",
      NEXT_PUBLIC_DEMO_TOKEN: "tok-public",
    });
    expect(config.bearerToken).toBe("tok-public");
  });

  it("real-peers uses CASE_API_BEARER_TOKEN when set", () => {
    const config = loadShellConfig({
      NEXT_PUBLIC_SHELL_MODE: "real-peers",
      CASE_API_BEARER_TOKEN: "tok-server",
      NEXT_PUBLIC_DEMO_TOKEN: "tok-public",
    });
    expect(config.bearerToken).toBe("tok-server");
  });

  it("real-peers refuses NEXT_PUBLIC_DEMO_TOKEN-only bearer", () => {
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
    expect((caught as PeerError).message).toMatch(/CASE_API_BEARER_TOKEN/);
    expect((caught as PeerError).message).toMatch(/NEXT_PUBLIC_/);
  });

  it("real-peers refuses missing server token even without public token", () => {
    expect(() =>
      loadShellConfig({
        NEXT_PUBLIC_SHELL_MODE: "real-peers",
      }),
    ).toThrow(PeerError);
  });
});
