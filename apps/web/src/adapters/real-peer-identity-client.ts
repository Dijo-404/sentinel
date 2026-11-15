import { isIP } from "node:net";
import {
  type ChallengeAccepted,
  type IdentityNotification,
  type IdentityUser,
  type Invitation,
  type LoginResult,
  type PatchProfileInput,
  type PortalRole,
  type RegisterResult,
  type SessionRecord,
  type WorkspaceAssignment,
  ROLE_LABELS,
  STAFF_ROLES,
} from "../../tests/stubs/identity";
import type { IdentityClient, InviteStaffInput, MeResult } from "@/lib/server/identity-client";
import { identityRoleToPortal, staffInviteRoleToIdentity } from "@/lib/server/identity-roles";
import { PeerError, isApiError } from "@/domain/types";

export type RealPeerIdentityOptions = {
  baseUrl: string;
  fetchImpl?: typeof fetch;
};

/**
 * Real-peer identity.v1 adapter (server-only).
 * Failures stay visible — never falls back to the fixture stub.
 */
export function createRealPeerIdentityClient(options: RealPeerIdentityOptions): IdentityClient {
  const base = options.baseUrl.replace(/\/$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;

  if (!base) {
    throw new PeerError(
      "PEER_UNAVAILABLE",
      "IDENTITY_BASE_URL is required in real-peers mode",
      "cfg-identity-missing-base",
      503,
    );
  }

  async function request(
    method: string,
    path: string,
    init?: {
      body?: unknown;
      bearer?: string;
      headers?: Record<string, string>;
      okStatuses?: number[];
    },
  ): Promise<{ status: number; json: unknown; requestId: string }> {
    const requestId = `web-id-${crypto.randomUUID()}`;
    let response: Response;
    try {
      response = await fetchImpl(`${base}${path}`, {
        method,
        headers: {
          Accept: "application/json",
          "X-Request-Id": requestId,
          ...(init?.bearer ? { Authorization: `Bearer ${init.bearer}` } : {}),
          ...(init?.body ? { "Content-Type": "application/json" } : {}),
          ...(init?.headers ?? {}),
        },
        body: init?.body ? JSON.stringify(init.body) : undefined,
      });
    } catch (err) {
      throw new PeerError(
        "PEER_UNAVAILABLE",
        err instanceof Error ? err.message : "Network failure contacting identity",
        requestId,
        503,
      );
    }

    let json: unknown = undefined;
    const text = await response.text();
    if (text) {
      try {
        json = JSON.parse(text);
      } catch {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Identity peer returned non-JSON body",
          requestId,
          response.status,
        );
      }
    }

    const okStatuses = init?.okStatuses ?? [200, 201];
    if (!okStatuses.includes(response.status)) {
      if (isApiError(json)) {
        throw new PeerError(json.code, json.message, json.request_id, response.status);
      }
      throw new PeerError(
        response.status === 401
          ? "UNAUTHORIZED"
          : response.status === 403
            ? "FORBIDDEN"
            : response.status === 503
              ? "PEER_UNAVAILABLE"
              : "PEER_ERROR",
        `Identity peer returned HTTP ${response.status}`,
        requestId,
        response.status,
      );
    }

    return { status: response.status, json, requestId };
  }

  async function loadMe(sessionToken: string): Promise<MeResult | null> {
    try {
      const { json, requestId } = await request("GET", "/v1/auth/me", {
        bearer: sessionToken,
        okStatuses: [200],
      });
      return mapMe(json, sessionToken, requestId);
    } catch (err) {
      if (
        err instanceof PeerError &&
        (err.httpStatus === 401 ||
          err.code === "UNAUTHORIZED" ||
          err.httpStatus === 403 ||
          err.code === "FORBIDDEN")
      ) {
        return null;
      }
      throw err;
    }
  }

  async function selectWorkspaceAssignment(
    sessionToken: string,
    assignmentId: string,
  ): Promise<SessionRecord | null> {
    try {
      const { json, requestId } = await request("POST", "/v1/auth/workspaces/select", {
        bearer: sessionToken,
        body: { assignment_id: assignmentId },
        okStatuses: [200],
      });
      if (!json || typeof json !== "object") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Workspace select response is not an object",
          requestId,
        );
      }
      const body = json as Record<string, unknown>;
      const token = typeof body.session_token === "string" ? body.session_token : null;
      const expiresAt = typeof body.expires_at === "string" ? body.expires_at : null;
      const active = body.active_assignment;
      if (!token || !expiresAt || !active || typeof active !== "object") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Workspace select missing session_token or assignment",
          requestId,
        );
      }
      const assignment = mapWorkspace(active as Record<string, unknown>, requestId);
      return {
        session_id: token,
        user_id: "",
        active_assignment_id: assignment.assignment_id,
        issued_at: new Date().toISOString(),
        expires_at: expiresAt,
        revoked: false,
      } satisfies SessionRecord;
    } catch (err) {
      if (
        err instanceof PeerError &&
        (err.httpStatus === 401 ||
          err.code === "UNAUTHORIZED" ||
          err.httpStatus === 403 ||
          err.code === "FORBIDDEN")
      ) {
        return null;
      }
      throw err;
    }
  }

  async function registerPublicAccount(
    input: Parameters<IdentityClient["registerCustomer"]>[0] & { business_name?: string },
    type: "customer" | "merchant",
  ): Promise<RegisterResult> {
    const allowed = [
      "email",
      "password",
      "display_name",
      "language",
      ...(type === "merchant" ? ["business_name"] : []),
    ];
    if (
      Object.entries(input).some(([key, value]) => value !== undefined && !allowed.includes(key))
    ) {
      return { ok: false, code: "PRIVILEGED_FIELDS_REJECTED" };
    }
    try {
      const { json, requestId } = await request("POST", `/v1/auth/${type}/register`, {
        body: {
          email: input.email,
          password: input.password,
          display_name: input.display_name,
          ...(type === "merchant" ? { business_name: input.business_name } : {}),
          ...(input.language ? { preferred_language: input.language } : {}),
        },
        okStatuses: [201],
      });
      return mapRegisterSuccess(json, requestId);
    } catch (err) {
      if (err instanceof PeerError) {
        if (err.code === "CONFLICT" || err.httpStatus === 409) {
          return { ok: false, code: "ALREADY_EXISTS" };
        }
        if (err.code === "INVALID_INPUT" || err.httpStatus === 422) {
          const msg = err.message.toLowerCase();
          if (
            msg.includes("role") ||
            msg.includes("privileged") ||
            msg.includes("tenant") ||
            msg.includes("account_type")
          ) {
            return { ok: false, code: "PRIVILEGED_FIELDS_REJECTED" };
          }
          return { ok: false, code: "INVALID_INPUT" };
        }
      }
      throw err;
    }
  }

  return {
    async login(email, password, clientIp): Promise<LoginResult> {
      try {
        const { json, requestId } = await request("POST", "/v1/auth/login", {
          body: { email, password },
          ...(clientIp && isIP(clientIp) ? { headers: { "X-Forwarded-For": clientIp } } : {}),
          okStatuses: [200],
        });
        return mapLoginSuccess(json, requestId);
      } catch (err) {
        if (err instanceof PeerError) {
          if (err.code === "ACCOUNT_NOT_FOUND") return { ok: false, code: "ACCOUNT_NOT_FOUND" };
          if (err.code === "RATE_LIMITED" || err.httpStatus === 429)
            return { ok: false, code: "RATE_LIMITED" };
          if (err.httpStatus === 401 || err.code === "UNAUTHORIZED") {
            return { ok: false, code: "INVALID_CREDENTIALS" };
          }
          if (err.httpStatus === 403 || err.code === "FORBIDDEN") {
            const msg = err.message.toLowerCase();
            if (msg.includes("pending")) return { ok: false, code: "PENDING" };
            if (msg.includes("suspend")) return { ok: false, code: "SUSPENDED" };
            return { ok: false, code: "INVALID_CREDENTIALS" };
          }
        }
        throw err;
      }
    },

    registerCustomer: (input) => registerPublicAccount(input, "customer"),
    registerMerchant: (input) => registerPublicAccount(input, "merchant"),

    async resolveSession(sessionToken) {
      return loadMe(sessionToken);
    },

    async getMe(sessionToken): Promise<MeResult | null> {
      return loadMe(sessionToken);
    },

    async patchProfile(sessionToken, input: PatchProfileInput) {
      const { json, requestId } = await request("PATCH", "/v1/auth/me", {
        bearer: sessionToken,
        body: input,
        okStatuses: [200],
      });
      if (!json || typeof json !== "object") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Patch profile response is not an object",
          requestId,
        );
      }
      const userRaw = (json as { user?: unknown }).user;
      return { user: mapPublicUser(userRaw, requestId) };
    },

    async listNotifications(sessionToken) {
      const { json, requestId } = await request("GET", "/v1/auth/notifications", {
        bearer: sessionToken,
        okStatuses: [200],
      });
      if (!json || typeof json !== "object") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Notifications response is not an object",
          requestId,
        );
      }
      const rows = (json as { notifications?: unknown }).notifications;
      if (!Array.isArray(rows)) {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Notifications missing notifications array",
          requestId,
        );
      }
      return {
        notifications: rows.map((row) => mapNotification(row, requestId)),
      };
    },

    async markNotificationRead(sessionToken, notificationId) {
      const { json, requestId } = await request(
        "POST",
        `/v1/auth/notifications/${encodeURIComponent(notificationId)}/read`,
        {
          bearer: sessionToken,
          okStatuses: [200],
        },
      );
      if (!json || typeof json !== "object") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Mark-read response is not an object",
          requestId,
        );
      }
      const body = json as Record<string, unknown>;
      if (typeof body.notification_id !== "string" || typeof body.read_at !== "string") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Mark-read missing notification_id or read_at",
          requestId,
        );
      }
      return {
        notification_id: body.notification_id,
        read_at: body.read_at,
      };
    },

    async requestVerify(sessionToken) {
      const { json, requestId } = await request("POST", "/v1/auth/verify/request", {
        bearer: sessionToken,
        body: {},
        okStatuses: [202],
      });
      return mapChallengeAccepted(json, requestId);
    },

    async confirmVerify(sessionToken, code) {
      const { json, requestId } = await request("POST", "/v1/auth/verify/confirm", {
        bearer: sessionToken,
        body: { code },
        okStatuses: [200],
      });
      if (!json || typeof json !== "object") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Verify confirm response is not an object",
          requestId,
        );
      }
      const body = json as Record<string, unknown>;
      if (body.email_verified !== true) {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Verify confirm missing email_verified",
          requestId,
        );
      }
      return {
        user: mapPublicUser(body.user, requestId),
        email_verified: true as const,
      };
    },

    async mfaChallenge(sessionToken) {
      const { json, requestId } = await request("POST", "/v1/auth/mfa/challenge", {
        bearer: sessionToken,
        okStatuses: [202],
      });
      return mapChallengeAccepted(json, requestId);
    },

    async mfaVerify(sessionToken, code) {
      const { json, requestId } = await request("POST", "/v1/auth/mfa/verify", {
        bearer: sessionToken,
        body: { code },
        okStatuses: [200],
      });
      if (!json || typeof json !== "object") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "MFA verify response is not an object",
          requestId,
        );
      }
      const body = json as Record<string, unknown>;
      if (body.mfa_verified !== true || typeof body.mfa_verified_at !== "string") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "MFA verify missing mfa_verified fields",
          requestId,
        );
      }
      return {
        mfa_verified: true as const,
        mfa_verified_at: body.mfa_verified_at,
      };
    },

    async forgotPassword(email) {
      const { json, requestId } = await request("POST", "/v1/auth/password/forgot", {
        body: { email },
        okStatuses: [202],
      });
      return mapChallengeAccepted(json, requestId);
    },

    async sandboxLatestCode(sessionToken, purpose) {
      const { json, requestId } = await request(
        "GET",
        `/v1/auth/sandbox/latest-code?purpose=${encodeURIComponent(purpose)}`,
        {
          bearer: sessionToken,
          okStatuses: [200],
        },
      );
      return mapSandboxCode(json, requestId);
    },

    async sandboxPasswordResetCode(email, sandboxToken) {
      const { json, requestId } = await request(
        "GET",
        `/v1/auth/sandbox/password-reset-code?email=${encodeURIComponent(email)}`,
        {
          headers: { "X-Identity-Sandbox-Token": sandboxToken },
          okStatuses: [200],
        },
      );
      return mapSandboxCode(json, requestId);
    },

    async resetPassword(input) {
      const { json, requestId } = await request("POST", "/v1/auth/password/reset", {
        body: {
          email: input.email,
          code: input.code,
          new_password: input.new_password,
        },
        okStatuses: [200],
      });
      if (!json || typeof json !== "object") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Password reset response is not an object",
          requestId,
        );
      }
      if ((json as { status?: unknown }).status !== "reset") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Password reset missing status=reset",
          requestId,
        );
      }
      return { status: "reset" as const };
    },

    async listWorkspaces(sessionToken) {
      const { json, requestId } = await request("GET", "/v1/auth/workspaces", {
        bearer: sessionToken,
        okStatuses: [200],
      });
      if (!json || typeof json !== "object") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Workspaces response is not an object",
          requestId,
        );
      }
      const body = json as Record<string, unknown>;
      const workspaces = mapWorkspaceList(body.workspaces, requestId);
      const activeRaw = body.active_assignment;
      const active_assignment =
        activeRaw && typeof activeRaw === "object"
          ? mapWorkspace(activeRaw as Record<string, unknown>, requestId)
          : null;
      return { workspaces, active_assignment };
    },

    async selectWorkspace(sessionToken, assignmentId) {
      return selectWorkspaceAssignment(sessionToken, assignmentId);
    },

    async selectAssignment(sessionToken, assignmentId) {
      return selectWorkspaceAssignment(sessionToken, assignmentId);
    },

    async logout(sessionToken) {
      try {
        await request("POST", "/v1/auth/logout", {
          bearer: sessionToken,
          okStatuses: [200],
        });
      } catch (err) {
        if (err instanceof PeerError && (err.httpStatus === 401 || err.code === "UNAUTHORIZED")) {
          return;
        }
        throw err;
      }
    },

    async listStaffUsers(sessionToken) {
      try {
        const { json, requestId } = await request("GET", "/v1/admin/users", {
          bearer: sessionToken,
          okStatuses: [200],
        });
        if (!json || typeof json !== "object") {
          throw new PeerError(
            "MALFORMED_PEER_RESPONSE",
            "Admin users response is not an object",
            requestId,
          );
        }
        const users = (json as { users?: unknown }).users;
        if (!Array.isArray(users)) {
          throw new PeerError(
            "MALFORMED_PEER_RESPONSE",
            "Admin users missing users array",
            requestId,
          );
        }
        return users.map((u) => mapStaffUser(u, requestId));
      } catch (err) {
        if (
          err instanceof PeerError &&
          (err.httpStatus === 401 ||
            err.code === "UNAUTHORIZED" ||
            err.httpStatus === 403 ||
            err.code === "FORBIDDEN")
        ) {
          return { error: "FORBIDDEN" as const };
        }
        throw err;
      }
    },

    async listInvitations(sessionToken) {
      try {
        const { json, requestId } = await request("GET", "/v1/admin/invitations", {
          bearer: sessionToken,
          okStatuses: [200],
        });
        if (!json || typeof json !== "object") {
          throw new PeerError(
            "MALFORMED_PEER_RESPONSE",
            "Admin invitations response is not an object",
            requestId,
          );
        }
        const invitations = (json as { invitations?: unknown }).invitations;
        if (!Array.isArray(invitations)) {
          throw new PeerError(
            "MALFORMED_PEER_RESPONSE",
            "Admin invitations missing invitations array",
            requestId,
          );
        }
        return invitations.map((inv) => mapInvitation(inv, requestId));
      } catch (err) {
        if (
          err instanceof PeerError &&
          (err.httpStatus === 401 ||
            err.code === "UNAUTHORIZED" ||
            err.httpStatus === 403 ||
            err.code === "FORBIDDEN")
        ) {
          return { error: "FORBIDDEN" as const };
        }
        throw err;
      }
    },

    async inviteStaff(sessionToken, input: InviteStaffInput) {
      const role_id = staffInviteRoleToIdentity(input.role_id);
      if (!role_id || role_id === "customer") {
        return {
          ok: false,
          code: "INVALID_ROLE",
          message: "Customer role cannot be invited via staff invitation",
        };
      }
      try {
        const { json, requestId } = await request("POST", "/v1/admin/invitations", {
          bearer: sessionToken,
          body: {
            display_name: input.display_name,
            work_email: input.work_email,
            tenant_id: input.tenant_id,
            role_id,
            ...(input.scope ? { scope: input.scope } : {}),
            ...(input.reason ? { reason: input.reason } : {}),
            ...(input.idempotency_key ? { idempotency_key: input.idempotency_key } : {}),
          },
          okStatuses: [201],
        });
        if (!json || typeof json !== "object") {
          throw new PeerError(
            "MALFORMED_PEER_RESPONSE",
            "Invite response is not an object",
            requestId,
          );
        }
        const invitationRaw = (json as { invitation?: unknown }).invitation;
        if (!invitationRaw) {
          throw new PeerError(
            "MALFORMED_PEER_RESPONSE",
            "Invite response missing invitation",
            requestId,
          );
        }
        return {
          ok: true as const,
          invitation: mapInvitation(invitationRaw, requestId),
        };
      } catch (err) {
        if (err instanceof PeerError) {
          if (err.httpStatus === 403 || err.code === "FORBIDDEN") {
            return {
              ok: false,
              code: "FORBIDDEN",
              message: err.message,
            };
          }
          if (err.code === "INVALID_INPUT" || err.httpStatus === 422) {
            const msg = err.message.toLowerCase();
            if (msg.includes("role") || msg.includes("customer")) {
              return {
                ok: false,
                code: "INVALID_ROLE",
                message: err.message,
              };
            }
            return {
              ok: false,
              code: "INVALID_INPUT",
              message: err.message,
            };
          }
          if (err.code === "CONFLICT" || err.httpStatus === 409) {
            return {
              ok: false,
              code: "DUPLICATE",
              message: err.message,
            };
          }
        }
        throw err;
      }
    },

    async acceptInvitation(input) {
      try {
        const { json, requestId } = await request("POST", "/v1/auth/accept-invitation", {
          body: {
            token: input.token,
            email: input.email,
            password: input.password,
            ...(input.display_name ? { display_name: input.display_name } : {}),
          },
          okStatuses: [201],
        });
        return mapAcceptInvitation(json, requestId);
      } catch (err) {
        if (err instanceof PeerError) {
          if (
            err.httpStatus === 401 ||
            err.code === "UNAUTHORIZED" ||
            err.httpStatus === 403 ||
            err.code === "FORBIDDEN"
          ) {
            return {
              ok: false as const,
              code: err.code === "UNAUTHORIZED" ? "UNAUTHORIZED" : "FORBIDDEN",
              message: err.message,
            };
          }
          if (err.httpStatus === 409 || err.code === "CONFLICT") {
            return {
              ok: false as const,
              code: "CONFLICT",
              message: err.message,
            };
          }
          if (err.httpStatus === 422 || err.code === "INVALID_INPUT") {
            return {
              ok: false as const,
              code: "INVALID_INPUT",
              message: err.message,
            };
          }
        }
        throw err;
      }
    },

    async assignableRoles() {
      return STAFF_ROLES.map((role_id) => ({
        role_id,
        label: ROLE_LABELS[role_id],
      }));
    },
  };
}

function mapLoginSuccess(json: unknown, requestId: string): LoginResult {
  if (!json || typeof json !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Login response is not an object", requestId);
  }
  const body = json as Record<string, unknown>;
  const token = typeof body.session_token === "string" ? body.session_token : null;
  const expiresAt = typeof body.expires_at === "string" ? body.expires_at : null;
  if (!token || !expiresAt) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Login missing session_token or expires_at",
      requestId,
    );
  }
  const user = mapPublicUser(body.user, requestId);
  const workspaces = mapWorkspaceList(body.workspaces, requestId);
  const active = body.active_assignment;
  const activeAssignment =
    active && typeof active === "object"
      ? mapWorkspace(active as Record<string, unknown>, requestId)
      : workspaces[0];
  if (!activeAssignment) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Login missing workspaces", requestId);
  }
  user.assignments = workspaces;
  const session: SessionRecord = {
    session_id: token,
    user_id: user.user_id,
    active_assignment_id: activeAssignment.assignment_id,
    issued_at: new Date().toISOString(),
    expires_at: expiresAt,
    revoked: false,
  };
  return { ok: true, session, user, workspaces };
}

function mapRegisterSuccess(json: unknown, requestId: string): RegisterResult {
  if (!json || typeof json !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Register response is not an object", requestId);
  }
  const body = json as Record<string, unknown>;
  const token = typeof body.session_token === "string" ? body.session_token : null;
  const expiresAt = typeof body.expires_at === "string" ? body.expires_at : null;
  if (!token || !expiresAt) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Register missing session_token or expires_at",
      requestId,
    );
  }
  const user = mapPublicUser(body.user, requestId);
  const assignment = mapWorkspace(body.assignment as Record<string, unknown>, requestId);
  user.assignments = [assignment];
  const session: SessionRecord = {
    session_id: token,
    user_id: user.user_id,
    active_assignment_id: assignment.assignment_id,
    issued_at: new Date().toISOString(),
    expires_at: expiresAt,
    revoked: false,
  };
  return { ok: true, session, user };
}

function mapMe(
  json: unknown,
  sessionToken: string,
  requestId: string,
): {
  session: SessionRecord;
  user: IdentityUser;
  assignment: WorkspaceAssignment;
} | null {
  if (!json || typeof json !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Me response is not an object", requestId);
  }
  const body = json as Record<string, unknown>;
  const user = mapPublicUser(body.user, requestId);
  const workspaces = mapWorkspaceList(body.workspaces, requestId);
  user.assignments = workspaces;
  const activeRaw = body.active_assignment;
  if (!activeRaw || typeof activeRaw !== "object") {
    return null;
  }
  const assignment = mapWorkspace(activeRaw as Record<string, unknown>, requestId);
  const peerExpires = typeof body.expires_at === "string" ? body.expires_at : null;
  const session: SessionRecord = {
    session_id: sessionToken,
    user_id: user.user_id,
    active_assignment_id: assignment.assignment_id,
    issued_at: new Date().toISOString(),
    expires_at: peerExpires ?? new Date(Date.now() + 12 * 3600_000).toISOString(),
    revoked: false,
  };
  return { session, user, assignment };
}

function mapAcceptInvitation(
  json: unknown,
  requestId: string,
):
  | {
      ok: true;
      session: SessionRecord;
      user: IdentityUser;
      assignment: WorkspaceAssignment;
    }
  | { ok: false; code: string; message: string } {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Accept-invitation response is not an object",
      requestId,
    );
  }
  const body = json as Record<string, unknown>;
  const token = typeof body.session_token === "string" ? body.session_token : null;
  const expiresAt = typeof body.expires_at === "string" ? body.expires_at : null;
  if (!token || !expiresAt) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Accept-invitation missing session_token or expires_at",
      requestId,
    );
  }
  const user = mapPublicUser(body.user, requestId);
  if (!body.assignment || typeof body.assignment !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Accept-invitation missing assignment",
      requestId,
    );
  }
  const assignment = mapWorkspace(body.assignment as Record<string, unknown>, requestId);
  user.assignments = [assignment];
  const session: SessionRecord = {
    session_id: token,
    user_id: user.user_id,
    active_assignment_id: assignment.assignment_id,
    issued_at: new Date().toISOString(),
    expires_at: expiresAt,
    revoked: false,
  };
  return { ok: true, session, user, assignment };
}

function mapPublicUser(raw: unknown, requestId: string): IdentityUser {
  if (!raw || typeof raw !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "User payload missing", requestId);
  }
  const u = raw as Record<string, unknown>;
  if (typeof u.user_id !== "string" || typeof u.email !== "string") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "User missing user_id or email", requestId);
  }
  const statusRaw = typeof u.status === "string" ? u.status.toUpperCase() : "ACTIVE";
  const account_status =
    statusRaw === "SUSPENDED" || statusRaw === "PENDING" ? statusRaw : "ACTIVE";
  const account_class = u.account_type === "staff" ? ("staff" as const) : ("customer" as const);
  return {
    user_id: u.user_id,
    email: u.email,
    display_name: typeof u.display_name === "string" ? u.display_name : "",
    preferred_language: typeof u.preferred_language === "string" ? u.preferred_language : "",
    email_verified_at: typeof u.email_verified_at === "string" ? u.email_verified_at : null,
    password: "",
    account_status,
    account_class,
    assignments: [],
  };
}

function mapNotification(raw: unknown, requestId: string): IdentityNotification {
  if (!raw || typeof raw !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Notification payload missing", requestId);
  }
  const n = raw as Record<string, unknown>;
  if (
    typeof n.notification_id !== "string" ||
    typeof n.title !== "string" ||
    typeof n.body !== "string" ||
    typeof n.created_at !== "string"
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Notification missing required fields",
      requestId,
    );
  }
  return {
    notification_id: n.notification_id,
    title: n.title,
    body: n.body,
    created_at: n.created_at,
    read_at: typeof n.read_at === "string" ? n.read_at : null,
  };
}

function mapChallengeAccepted(json: unknown, requestId: string): ChallengeAccepted {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Challenge response is not an object",
      requestId,
    );
  }
  const body = json as Record<string, unknown>;
  if (body.status !== "accepted") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Challenge response missing status=accepted",
      requestId,
    );
  }
  const result: ChallengeAccepted = { status: "accepted" };
  if (typeof body.sandbox_code === "string") {
    result.sandbox_code = body.sandbox_code;
  }
  if (typeof body.sandbox_hint === "string") {
    result.sandbox_hint = body.sandbox_hint;
  }
  return result;
}

function mapSandboxCode(json: unknown, requestId: string): { code: string } {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Sandbox code response is not an object",
      requestId,
    );
  }
  const body = json as Record<string, unknown>;
  if (typeof body.code !== "string" || !body.code) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Sandbox code response missing code", requestId);
  }
  return { code: body.code };
}

function mapStaffUser(raw: unknown, requestId: string): IdentityUser {
  const user = mapPublicUser(raw, requestId);
  const assignmentsRaw =
    raw && typeof raw === "object" ? (raw as { assignments?: unknown }).assignments : undefined;
  user.assignments = mapWorkspaceList(assignmentsRaw, requestId);
  return user;
}

function mapWorkspaceList(raw: unknown, requestId: string): WorkspaceAssignment[] {
  if (!Array.isArray(raw)) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Workspaces must be an array", requestId);
  }
  return raw.map((item) => mapWorkspace(item as Record<string, unknown>, requestId));
}

function mapWorkspace(raw: Record<string, unknown>, requestId: string): WorkspaceAssignment {
  if (typeof raw.assignment_id !== "string" || typeof raw.tenant_id !== "string") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Workspace missing assignment_id or tenant_id",
      requestId,
    );
  }
  const roleId = typeof raw.role_id === "string" ? raw.role_id : "";
  const role = identityRoleToPortal(roleId);
  if (!role) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      `Unknown identity role_id: ${roleId}`,
      requestId,
    );
  }
  const scope: Record<string, string> = {};
  if (typeof raw.merchant_ref === "string" && raw.merchant_ref) {
    scope.merchant_id = raw.merchant_ref;
  }
  if (typeof raw.team_id === "string" && raw.team_id) {
    scope.team_id = raw.team_id;
  }
  return {
    assignment_id: raw.assignment_id,
    role,
    tenant_id: raw.tenant_id,
    label: ROLE_LABELS[role as PortalRole] ?? role,
    ...(Object.keys(scope).length ? { scope } : {}),
  };
}

function mapInvitation(raw: unknown, requestId: string): Invitation {
  if (!raw || typeof raw !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Invitation payload missing", requestId);
  }
  const inv = raw as Record<string, unknown>;
  const roleId = typeof inv.role_id === "string" ? inv.role_id : "";
  const portal = identityRoleToPortal(roleId);
  if (!portal || portal === "customer") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      `Unknown invitation role_id: ${roleId}`,
      requestId,
    );
  }
  const statusRaw = typeof inv.status === "string" ? inv.status.toUpperCase() : "PENDING";
  const status =
    statusRaw === "ACCEPTED" || statusRaw === "REVOKED" || statusRaw === "EXPIRED"
      ? statusRaw
      : "PENDING";
  return {
    invitation_id: typeof inv.invitation_id === "string" ? inv.invitation_id : "",
    work_email: typeof inv.work_email === "string" ? inv.work_email : "",
    display_name: typeof inv.display_name === "string" ? inv.display_name : "",
    tenant_id: typeof inv.tenant_id === "string" ? inv.tenant_id : "",
    role: portal,
    scope: {},
    status,
    created_by: "",
    expires_at: typeof inv.expires_at === "string" ? inv.expires_at : new Date().toISOString(),
  };
}
