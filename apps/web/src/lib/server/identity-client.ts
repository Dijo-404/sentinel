import {
  getSharedIdentityStub,
  type StubIdentity,
} from "../../../tests/stubs/identity";
import { PeerError } from "@/domain/types";

export type IdentityMode = "fixture" | "real-peers";

/**
 * Resolve identity adapter. Fixture mode uses the local stub.
 * Real-peers refuses public demo tokens and requires a future identity peer.
 */
export function getIdentityClient(
  env: Record<string, string | undefined> = process.env as Record<
    string,
    string | undefined
  >,
): StubIdentity {
  const mode = (env.NEXT_PUBLIC_SHELL_MODE ?? "fixture") as IdentityMode;
  if (mode === "real-peers") {
    if (env.NEXT_PUBLIC_DEMO_TOKEN && !env.IDENTITY_BEARER_TOKEN) {
      throw new PeerError(
        "INVALID_CONFIG",
        "IDENTITY_BEARER_TOKEN is required in real-peers mode; never put secrets in NEXT_PUBLIC_*",
        "cfg-identity-public-token",
      );
    }
    if (!env.IDENTITY_BASE_URL || !env.IDENTITY_BEARER_TOKEN) {
      throw new PeerError(
        "PEER_UNAVAILABLE",
        "Identity peer not configured for real-peers mode",
        "cfg-identity-missing",
      );
    }
    throw new PeerError(
      "PEER_UNAVAILABLE",
      "Identity real-peer adapter not wired in this module slice",
      "identity-real-peer",
    );
  }
  return getSharedIdentityStub();
}
