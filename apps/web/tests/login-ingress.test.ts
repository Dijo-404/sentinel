import { describe, expect, it } from "vitest";
import { trustedLoginClientIp } from "@/lib/server/auth";
import { createRealPeerIdentityClient } from "@/adapters/real-peer-identity-client";

const token = "a".repeat(32);
describe("login ingress client identity", () => {
  it("ignores arbitrary forwarded and unconfigured ingress headers", () => {
    const headers = new Headers({
      "x-forwarded-for": "198.51.100.9",
      "x-sentinel-client-ip": "198.51.100.8",
      "x-sentinel-ingress-token": token,
    });
    expect(trustedLoginClientIp(headers, {})).toBeUndefined();
    expect(
      trustedLoginClientIp(headers, { WEB_TRUSTED_INGRESS_TOKEN: "b".repeat(32) }),
    ).toBeUndefined();
    expect(trustedLoginClientIp(headers, { WEB_TRUSTED_INGRESS_TOKEN: "short" })).toBeUndefined();
  });
  it.each(["198.51.100.8", "2001:db8::8"])("accepts authenticated single literal IP %s", (ip) => {
    const headers = new Headers({ "x-sentinel-client-ip": ip, "x-sentinel-ingress-token": token });
    expect(trustedLoginClientIp(headers, { WEB_TRUSTED_INGRESS_TOKEN: token })).toBe(ip);
  });
  it.each(["", "unknown", "198.51.100.1, 198.51.100.2", "198.51.100.1:80", "127.1"])(
    "omits missing/malformed address %s",
    (ip) => {
      const headers = new Headers({
        "x-sentinel-client-ip": ip,
        "x-sentinel-ingress-token": token,
      });
      expect(trustedLoginClientIp(headers, { WEB_TRUSTED_INGRESS_TOKEN: token })).toBeUndefined();
      expect(
        trustedLoginClientIp(new Headers({ "x-sentinel-client-ip": "198.51.100.8" }), {
          WEB_TRUSTED_INGRESS_TOKEN: token,
        }),
      ).toBeUndefined();
    },
  );
  it("forwards only a verified client address on the login wire request", async () => {
    const sent: RequestInit[] = [];
    const client = createRealPeerIdentityClient({
      baseUrl: "http://identity.test",
      fetchImpl: async (_url, init) => {
        sent.push(init!);
        return Response.json(
          { code: "UNAUTHORIZED", message: "Invalid credentials", request_id: "test" },
          { status: 401 },
        );
      },
    });
    await client.login("user@example.test", "wrong", "198.51.100.8");
    expect(sent[0]!.headers).toMatchObject({ "X-Forwarded-For": "198.51.100.8" });
    await client.login("user@example.test", "wrong");
    expect(new Headers(sent[1]!.headers).has("X-Forwarded-For")).toBe(false);
    expect(new Headers(sent[0]!.headers).has("x-sentinel-ingress-token")).toBe(false);
  });
});
