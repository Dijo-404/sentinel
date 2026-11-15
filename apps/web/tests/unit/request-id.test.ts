import { afterEach, describe, expect, it, vi } from "vitest";
import { newRequestId } from "@/lib/request-id";

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe("newRequestId", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses crypto.randomUUID when available", () => {
    expect(newRequestId()).toMatch(V4);
  });

  it("falls back to getRandomValues in insecure contexts (plain HTTP)", () => {
    const real = globalThis.crypto;
    vi.stubGlobal("crypto", { getRandomValues: real.getRandomValues.bind(real) });
    const a = newRequestId();
    const b = newRequestId();
    expect(a).toMatch(V4);
    expect(a).not.toBe(b);
  });
});
