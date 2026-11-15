import {
  getSharedIdentityStub,
  type ChallengeAccepted,
  type IdentityNotification,
  type InviteResult,
  type LoginResult,
  type PatchProfileInput,
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

export type MeResult = {
  session: SessionRecord;
  user: IdentityUser;
  assignment: WorkspaceAssignment;
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
  resolveSession(sessionCredential: string): Promise<MeResult | null>;
  /** GET /v1/auth/me — same session binding as resolveSession. */
  getMe(sessionCredential: string): Promise<MeResult | null>;
  patchProfile(
    sessionCredential: string,
    input: PatchProfileInput,
  ): Promise<{ user: IdentityUser }>;
  listNotifications(sessionCredential: string): Promise<{ notifications: IdentityNotification[] }>;
  markNotificationRead(
    sessionCredential: string,
    notificationId: string,
  ): Promise<{ notification_id: string; read_at: string }>;
  requestVerify(sessionCredential: string): Promise<ChallengeAccepted>;
  confirmVerify(
    sessionCredential: string,
    code: string,
  ): Promise<{ user: IdentityUser; email_verified: true }>;
  mfaChallenge(sessionCredential: string): Promise<ChallengeAccepted>;
  mfaVerify(
    sessionCredential: string,
    code: string,
  ): Promise<{ mfa_verified: true; mfa_verified_at: string }>;
  forgotPassword(email: string): Promise<ChallengeAccepted>;
  /** Sandbox inbox: GET /v1/auth/sandbox/latest-code (session). */
  sandboxLatestCode(
    sessionCredential: string,
    purpose: "email_verify" | "mfa",
  ): Promise<{ code: string }>;
  /** Sandbox inbox: GET /v1/auth/sandbox/password-reset-code (token header). */
  sandboxPasswordResetCode(email: string, sandboxToken: string): Promise<{ code: string }>;
  resetPassword(input: {
    email: string;
    code: string;
    new_password: string;
  }): Promise<{ status: "reset" }>;
  listWorkspaces(sessionCredential: string): Promise<{
    workspaces: WorkspaceAssignment[];
    active_assignment: WorkspaceAssignment | null;
  }>;
  /** POST /v1/auth/workspaces/select — alias of selectAssignment. */
  selectWorkspace(sessionCredential: string, assignmentId: string): Promise<SessionRecord | null>;
  selectAssignment(sessionCredential: string, assignmentId: string): Promise<SessionRecord | null>;
  logout(sessionCredential: string): Promise<void>;
  listStaffUsers(sessionCredential: string): Promise<IdentityUser[] | { error: "FORBIDDEN" }>;
  listInvitations(sessionCredential: string): Promise<Invitation[] | { error: "FORBIDDEN" }>;
  inviteStaff(sessionCredential: string, input: InviteStaffInput): Promise<InviteResult>;
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
      role_id: Exclude<import("../../../tests/stubs/identity").PortalRole, "customer">;
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

type IdentityClientGlobal = typeof globalThis & {
  __sentinelFixtureIdentityClient?: IdentityClient;
};

function wrapFixtureStub(stub: StubIdentity): IdentityClient {
  return {
    login: async (email, password) => stub.login(email, password),
    registerCustomer: async (input) => stub.registerCustomer(input),
    resolveSession: async (sessionId) => stub.resolveSession(sessionId),
    getMe: async (sessionId) => stub.getMe(sessionId),
    patchProfile: async (sessionId, input) => {
      const result = stub.patchProfile(sessionId, input);
      if (!result.ok) {
        throw new PeerError(
          result.code,
          result.message,
          "fixture-patch-profile",
          result.code === "UNAUTHORIZED" ? 401 : 422,
        );
      }
      return { user: result.user };
    },
    listNotifications: async (sessionId) => {
      const result = stub.listNotifications(sessionId);
      if (!result) {
        throw new PeerError("UNAUTHORIZED", "Session required", "fixture-notifications", 401);
      }
      return result;
    },
    markNotificationRead: async (sessionId, notificationId) => {
      const result = stub.markNotificationRead(sessionId, notificationId);
      if (!result.ok) {
        throw new PeerError(
          result.code,
          result.code === "NOT_FOUND" ? "Notification not found" : "Session required",
          "fixture-notification-read",
          result.code === "NOT_FOUND" ? 404 : 401,
        );
      }
      return {
        notification_id: result.notification_id,
        read_at: result.read_at,
      };
    },
    requestVerify: async (sessionId) => {
      const result = stub.requestVerify(sessionId);
      if (!result) {
        throw new PeerError("UNAUTHORIZED", "Session required", "fixture-verify-request", 401);
      }
      return result;
    },
    confirmVerify: async (sessionId, code) => {
      const result = stub.confirmVerify(sessionId, code);
      if (!result.ok) {
        throw new PeerError(
          result.code,
          result.message,
          "fixture-verify-confirm",
          result.code === "UNAUTHORIZED" ? 401 : 400,
        );
      }
      return { user: result.user, email_verified: true };
    },
    mfaChallenge: async (sessionId) => {
      const result = stub.mfaChallenge(sessionId);
      if (!result) {
        throw new PeerError("UNAUTHORIZED", "Session required", "fixture-mfa-challenge", 401);
      }
      return result;
    },
    mfaVerify: async (sessionId, code) => {
      const result = stub.mfaVerify(sessionId, code);
      if (!result.ok) {
        throw new PeerError(
          result.code,
          result.message,
          "fixture-mfa-verify",
          result.code === "UNAUTHORIZED" ? 401 : 400,
        );
      }
      return {
        mfa_verified: true,
        mfa_verified_at: result.mfa_verified_at,
      };
    },
    forgotPassword: async (email) => stub.forgotPassword(email),
    // Fixture challenges already return sandbox_code; inbox helpers are real-peers.
    sandboxLatestCode: async (_sessionId, purpose) => {
      if (purpose === "email_verify") {
        return { code: "fixture-verify" };
      }
      throw new PeerError(
        "NOT_FOUND",
        "Sandbox MFA code not available in fixture inbox",
        "fixture-sandbox-latest",
        404,
      );
    },
    sandboxPasswordResetCode: async (_email, _sandboxToken) => ({
      code: "fixture-reset",
    }),
    resetPassword: async (input) => {
      const result = stub.resetPassword(input);
      if (!result.ok) {
        throw new PeerError(
          result.code,
          result.message,
          "fixture-password-reset",
          result.code === "INVALID_INPUT" ? 422 : 400,
        );
      }
      return { status: "reset" };
    },
    listWorkspaces: async (sessionId) => {
      const result = stub.listWorkspaces(sessionId);
      if (!result) {
        throw new PeerError("UNAUTHORIZED", "Session required", "fixture-workspaces", 401);
      }
      return result;
    },
    selectWorkspace: async (sessionId, assignmentId) =>
      stub.selectAssignment(sessionId, assignmentId),
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
  env: Record<string, string | undefined> = process.env as Record<string, string | undefined>,
  overrides?: { fetchImpl?: typeof fetch },
): IdentityClient {
  const mode = (env.NEXT_PUBLIC_SHELL_MODE ?? "real-peers") as IdentityMode;

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

  const g = globalThis as IdentityClientGlobal;
  if (!g.__sentinelFixtureIdentityClient) {
    g.__sentinelFixtureIdentityClient = wrapFixtureStub(getSharedIdentityStub());
  }
  return g.__sentinelFixtureIdentityClient;
}

/** Test helper: drop cached fixture wrapper after stub reset. */
export function resetIdentityClientCache(): void {
  const g = globalThis as IdentityClientGlobal;
  g.__sentinelFixtureIdentityClient = undefined;
}
