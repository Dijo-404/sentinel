import {
  getSharedIdentityStub,
  type InviteResult,
  type LoginResult,
  type RegisterResult,
  type SessionRecord,
  type StubIdentity,
  type IdentityUser,
  type Invitation,
  type WorkspaceAssignment,
} from "../../../tests/stubs/identity";
import { createRealPeerIdentityClient } from "@/adapters/real-peer-identity-client";
import { PeerError } from "@/domain/types";

export type IdentityMode = "fixture" | "real-peers";

export type InviteStaffInput = {
  display_name: string;
  work_email: string;
  tenant_id: string;
  role_id: string;
  scope?: Record<string, string>;
  reason?: string;
  idempotency_key?: string;
};

/**
 * Async identity port used by the web BFF.
 * Fixture wraps the local stub; real-peers calls identity.v1 over HTTP.
 */
export type IdentityClient = {
  login(email: string, password: string): Promise<LoginResult>;
  registerCustomer(input: {
    email: string;
    display_name: string;
    password: string;
    language?: string;
    roles?: unknown;
    tenant_id?: unknown;
    subject_refs?: unknown;
  }): Promise<RegisterResult>;
  resolveSession(sessionCredential: string): Promise<{
    session: SessionRecord;
    user: IdentityUser;
    assignment: WorkspaceAssignment;
  } | null>;
  selectAssignment(
    sessionCredential: string,
    assignmentId: string,
  ): Promise<SessionRecord | null>;
  logout(sessionCredential: string): Promise<void>;
  listStaffUsers(
    sessionCredential: string,
  ): Promise<IdentityUser[] | { error: "FORBIDDEN" }>;
  listInvitations(
    sessionCredential: string,
  ): Promise<Invitation[] | { error: "FORBIDDEN" }>;
  inviteStaff(
    sessionCredential: string,
    input: InviteStaffInput,
  ): Promise<InviteResult>;
  acceptInvitation(input: {
    token: string;
    email: string;
    password: string;
    display_name?: string;
  }): Promise<
    | {
        ok: true;
        session: SessionRecord;
        user: IdentityUser;
        assignment: WorkspaceAssignment;
      }
    | { ok: false; code: string; message: string }
  >;
  assignableRoles(): Promise<
    Array<{
      role_id: Exclude<
        import("../../../tests/stubs/identity").PortalRole,
        "customer"
      >;
      label: string;
    }>
  >;
};

const PUBLIC_IDENTITY_SECRET_KEYS = [
  "NEXT_PUBLIC_IDENTITY_BEARER_TOKEN",
  "NEXT_PUBLIC_IDENTITY_PASSWORD",
  "NEXT_PUBLIC_SESSION_TOKEN",
  "NEXT_PUBLIC_SESSION_SECRET",
] as const;

let cachedFixtureClient: IdentityClient | null = null;

function wrapFixtureStub(stub: StubIdentity): IdentityClient {
  return {
    login: async (email, password) => stub.login(email, password),
    registerCustomer: async (input) => stub.registerCustomer(input),
    resolveSession: async (sessionId) => stub.resolveSession(sessionId),
    selectAssignment: async (sessionId, assignmentId) =>
      stub.selectAssignment(sessionId, assignmentId),
    logout: async (sessionId) => {
      stub.logout(sessionId);
    },
    listStaffUsers: async (sessionCredential) => {
      const resolved = stub.resolveSession(sessionCredential);
      if (!resolved) return { error: "FORBIDDEN" };
      return stub.listStaffUsers(resolved.user.user_id);
    },
    listInvitations: async (sessionCredential) => {
      const resolved = stub.resolveSession(sessionCredential);
      if (!resolved) return { error: "FORBIDDEN" };
      return stub.listInvitations(resolved.user.user_id);
    },
    inviteStaff: async (sessionCredential, input) => {
      const resolved = stub.resolveSession(sessionCredential);
      if (!resolved) {
        return {
          ok: false,
          code: "FORBIDDEN",
          message: "Admin assignment required",
        };
      }
      return stub.inviteStaff(resolved.user.user_id, input);
    },
    acceptInvitation: async (input) => stub.acceptInvitation(input),
    assignableRoles: async () => stub.assignableRoles(),
  };
}

/**
 * Resolve identity adapter.
 * Fixture mode uses the local stub.
 * Real-peers calls identity.v1 at IDENTITY_BASE_URL and fails closed on peer errors.
 * Session tokens and passwords never come from NEXT_PUBLIC_*.
 */
export function getIdentityClient(
  env: Record<string, string | undefined> = process.env as Record<
    string,
    string | undefined
  >,
  overrides?: { fetchImpl?: typeof fetch },
): IdentityClient {
  const mode = (env.NEXT_PUBLIC_SHELL_MODE ?? "fixture") as IdentityMode;

  for (const key of PUBLIC_IDENTITY_SECRET_KEYS) {
    if (env[key]) {
      throw new PeerError(
        "INVALID_CONFIG",
        `${key} must not hold identity secrets; use server-only session cookie + IDENTITY_BASE_URL`,
        "cfg-identity-public-secret",
      );
    }
  }

  if (mode === "real-peers") {
    if (env.NEXT_PUBLIC_DEMO_TOKEN && !env.IDENTITY_BASE_URL) {
      throw new PeerError(
        "INVALID_CONFIG",
        "IDENTITY_BASE_URL is required in real-peers mode; never put secrets in NEXT_PUBLIC_*",
        "cfg-identity-public-token",
      );
    }
    if (!env.IDENTITY_BASE_URL) {
      throw new PeerError(
        "PEER_UNAVAILABLE",
        "IDENTITY_BASE_URL is required in real-peers mode",
        "cfg-identity-missing",
      );
    }
    return createRealPeerIdentityClient({
      baseUrl: env.IDENTITY_BASE_URL,
      fetchImpl: overrides?.fetchImpl,
    });
  }

  if (!cachedFixtureClient) {
    cachedFixtureClient = wrapFixtureStub(getSharedIdentityStub());
  }
  return cachedFixtureClient;
}

/** Test helper: drop cached fixture wrapper after stub reset. */
export function resetIdentityClientCache(): void {
  cachedFixtureClient = null;
}
