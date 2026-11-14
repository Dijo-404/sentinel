import {
  type IdentityUser,
  type Invitation,
  type LoginResult,
  type PortalRole,
  type RegisterResult,
  type SessionRecord,
  type WorkspaceAssignment,
  ROLE_LABELS,
  STAFF_ROLES,
} from "../../tests/stubs/identity";
import type {
  IdentityClient,
  InviteStaffInput,
} from "@/lib/server/identity-client";
import {
  identityRoleToPortal,
  staffInviteRoleToIdentity,
} from "@/lib/server/identity-roles";
import { PeerError, isApiError } from "@/domain/types";

export type RealPeerIdentityOptions = {
  baseUrl: string;
  fetchImpl?: typeof fetch;
};

/**
 * Real-peer identity.v1 adapter (server-only).
 * Failures stay visible — never falls back to the fixture stub.
 */
export function createRealPeerIdentityClient(
  options: RealPeerIdentityOptions,
): IdentityClient {
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
        },
        body: init?.body ? JSON.stringify(init.body) : undefined,
      });
    } catch (err) {
      throw new PeerError(
        "PEER_UNAVAILABLE",
        err instanceof Error
          ? err.message
          : "Network failure contacting identity",
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
        throw new PeerError(
          json.code,
          json.message,
          json.request_id,
          response.status,
        );
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

  return {
    async login(email, password): Promise<LoginResult> {
      try {
        const { json, requestId } = await request("POST", "/v1/auth/login", {
          body: { email, password },
          okStatuses: [200],
        });
        return mapLoginSuccess(json, requestId);
      } catch (err) {
        if (err instanceof PeerError) {
          if (err.httpStatus === 401 || err.code === "UNAUTHORIZED") {
            return { ok: false, code: "INVALID_CREDENTIALS" };
          }
          if (err.httpStatus === 403 || err.code === "FORBIDDEN") {
            const msg = err.message.toLowerCase();
            if (msg.includes("pending")) return { ok: false, code: "PENDING" };
            if (msg.includes("suspend"))
              return { ok: false, code: "SUSPENDED" };
            return { ok: false, code: "INVALID_CREDENTIALS" };
          }
        }
        throw err;
      }
    },

    async registerCustomer(input): Promise<RegisterResult> {
      if (
        input.roles !== undefined ||
        input.tenant_id !== undefined ||
        input.subject_refs !== undefined
      ) {
        return { ok: false, code: "PRIVILEGED_FIELDS_REJECTED" };
      }
      try {
        const { json, requestId } = await request(
          "POST",
          "/v1/auth/customer/register",
          {
            body: {
              email: input.email,
              password: input.password,
              display_name: input.display_name,
              ...(input.language ? { preferred_language: input.language } : {}),
            },
            okStatuses: [201],
          },
        );
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
    },

    async resolveSession(sessionToken) {
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
    },

    async selectAssignment(sessionToken, assignmentId) {
      try {
        const { json, requestId } = await request(
          "POST",
          "/v1/auth/workspaces/select",
          {
            bearer: sessionToken,
            body: { assignment_id: assignmentId },
            okStatuses: [200],
          },
        );
        if (!json || typeof json !== "object") {
          throw new PeerError(
            "MALFORMED_PEER_RESPONSE",
            "Workspace select response is not an object",
            requestId,
          );
        }
        const body = json as Record<string, unknown>;
        const token =
          typeof body.session_token === "string" ? body.session_token : null;
        const expiresAt =
          typeof body.expires_at === "string" ? body.expires_at : null;
        const active = body.active_assignment;
        if (!token || !expiresAt || !active || typeof active !== "object") {
          throw new PeerError(
            "MALFORMED_PEER_RESPONSE",
            "Workspace select missing session_token or assignment",
            requestId,
          );
        }
        const assignment = mapWorkspace(
          active as Record<string, unknown>,
          requestId,
        );
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
    },

    async logout(sessionToken) {
      try {
        await request("POST", "/v1/auth/logout", {
          bearer: sessionToken,
          okStatuses: [200],
        });
      } catch (err) {
        if (
          err instanceof PeerError &&
          (err.httpStatus === 401 || err.code === "UNAUTHORIZED")
        ) {
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
        const { json, requestId } = await request(
          "GET",
          "/v1/admin/invitations",
          {
            bearer: sessionToken,
            okStatuses: [200],
          },
        );
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
        const { json, requestId } = await request(
          "POST",
          "/v1/admin/invitations",
          {
            bearer: sessionToken,
            body: {
              display_name: input.display_name,
              work_email: input.work_email,
              tenant_id: input.tenant_id,
              role_id,
              ...(input.scope ? { scope: input.scope } : {}),
              ...(input.reason ? { reason: input.reason } : {}),
              ...(input.idempotency_key
                ? { idempotency_key: input.idempotency_key }
                : {}),
            },
            okStatuses: [201],
          },
        );
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
        const { json, requestId } = await request(
          "POST",
          "/v1/auth/accept-invitation",
          {
            body: {
              token: input.token,
              email: input.email,
              password: input.password,
              ...(input.display_name
                ? { display_name: input.display_name }
                : {}),
            },
            okStatuses: [201],
          },
        );
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
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Login response is not an object",
      requestId,
    );
  }
  const body = json as Record<string, unknown>;
  const token =
    typeof body.session_token === "string" ? body.session_token : null;
  const expiresAt =
    typeof body.expires_at === "string" ? body.expires_at : null;
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
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Login missing workspaces",
      requestId,
    );
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
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Register response is not an object",
      requestId,
    );
  }
  const body = json as Record<string, unknown>;
  const token =
    typeof body.session_token === "string" ? body.session_token : null;
  const expiresAt =
    typeof body.expires_at === "string" ? body.expires_at : null;
  if (!token || !expiresAt) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Register missing session_token or expires_at",
      requestId,
    );
  }
  const user = mapPublicUser(body.user, requestId);
  const assignment = mapWorkspace(
    body.assignment as Record<string, unknown>,
    requestId,
  );
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
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Me response is not an object",
      requestId,
    );
  }
  const body = json as Record<string, unknown>;
  const user = mapPublicUser(body.user, requestId);
  const workspaces = mapWorkspaceList(body.workspaces, requestId);
  user.assignments = workspaces;
  const activeRaw = body.active_assignment;
  if (!activeRaw || typeof activeRaw !== "object") {
    return null;
  }
  const assignment = mapWorkspace(
    activeRaw as Record<string, unknown>,
    requestId,
  );
  const peerExpires =
    typeof body.expires_at === "string" ? body.expires_at : null;
  const session: SessionRecord = {
    session_id: sessionToken,
    user_id: user.user_id,
    active_assignment_id: assignment.assignment_id,
    issued_at: new Date().toISOString(),
    expires_at:
      peerExpires ?? new Date(Date.now() + 12 * 3600_000).toISOString(),
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
  const token =
    typeof body.session_token === "string" ? body.session_token : null;
  const expiresAt =
    typeof body.expires_at === "string" ? body.expires_at : null;
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
  const assignment = mapWorkspace(
    body.assignment as Record<string, unknown>,
    requestId,
  );
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
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "User payload missing",
      requestId,
    );
  }
  const u = raw as Record<string, unknown>;
  if (typeof u.user_id !== "string" || typeof u.email !== "string") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "User missing user_id or email",
      requestId,
    );
  }
  const statusRaw =
    typeof u.status === "string" ? u.status.toUpperCase() : "ACTIVE";
  const account_status =
    statusRaw === "SUSPENDED" || statusRaw === "PENDING" ? statusRaw : "ACTIVE";
  const account_class =
    u.account_type === "staff" ? ("staff" as const) : ("customer" as const);
  return {
    user_id: u.user_id,
    email: u.email,
    display_name: typeof u.display_name === "string" ? u.display_name : "",
    password: "",
    account_status,
    account_class,
    assignments: [],
  };
}

function mapStaffUser(raw: unknown, requestId: string): IdentityUser {
  const user = mapPublicUser(raw, requestId);
  const assignmentsRaw =
    raw && typeof raw === "object"
      ? (raw as { assignments?: unknown }).assignments
      : undefined;
  user.assignments = mapWorkspaceList(assignmentsRaw, requestId);
  return user;
}

function mapWorkspaceList(
  raw: unknown,
  requestId: string,
): WorkspaceAssignment[] {
  if (!Array.isArray(raw)) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Workspaces must be an array",
      requestId,
    );
  }
  return raw.map((item) =>
    mapWorkspace(item as Record<string, unknown>, requestId),
  );
}

function mapWorkspace(
  raw: Record<string, unknown>,
  requestId: string,
): WorkspaceAssignment {
  if (
    typeof raw.assignment_id !== "string" ||
    typeof raw.tenant_id !== "string"
  ) {
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
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Invitation payload missing",
      requestId,
    );
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
  const statusRaw =
    typeof inv.status === "string" ? inv.status.toUpperCase() : "PENDING";
  const status =
    statusRaw === "ACCEPTED" ||
    statusRaw === "REVOKED" ||
    statusRaw === "EXPIRED"
      ? statusRaw
      : "PENDING";
  return {
    invitation_id:
      typeof inv.invitation_id === "string" ? inv.invitation_id : "",
    work_email: typeof inv.work_email === "string" ? inv.work_email : "",
    display_name: typeof inv.display_name === "string" ? inv.display_name : "",
    tenant_id: typeof inv.tenant_id === "string" ? inv.tenant_id : "",
    role: portal,
    scope: {},
    status,
    created_by: "",
    expires_at:
      typeof inv.expires_at === "string"
        ? inv.expires_at
        : new Date().toISOString(),
  };
}
