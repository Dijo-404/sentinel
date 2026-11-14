import { cookies } from "next/headers";
import {
  ROLE_LABELS,
  type IdentityUser,
  type PortalRole,
  type SessionRecord,
  type WorkspaceAssignment,
} from "../../../tests/stubs/identity";
import { getIdentityClient } from "./identity-client";

export const SESSION_COOKIE = "sentinel_session";

export type AuthSession = {
  session: SessionRecord;
  user: IdentityUser;
  assignment: WorkspaceAssignment;
  workspaces: WorkspaceAssignment[];
};

export type LoginAttempt =
  | {
      ok: true;
      session: AuthSession;
      role_match: boolean;
      requested_role: PortalRole;
    }
  | {
      ok: false;
      code: "INVALID_CREDENTIALS" | "SUSPENDED" | "PENDING" | "INVALID_INPUT";
      message: string;
    };

const GENERIC_AUTH_FAILURE =
  "Sign-in failed. Check your credentials and try again.";

export function portalPath(role: PortalRole): string {
  return `/${role}/dashboard`;
}

export function loginPath(role: PortalRole): string {
  return `/${role}/login`;
}

/**
 * Same-origin portal redirect only.
 * Normalize, reject `..` / schemes / protocol-relative, require `/{role}` or `/{role}/…`.
 */
export function isSafeInternalPath(
  path: string | null | undefined,
  role?: PortalRole,
): path is string {
  if (!path) return false;
  let decoded: string;
  try {
    decoded = decodeURIComponent(path);
  } catch {
    return false;
  }
  const pathOnly = decoded.split(/[?#]/, 1)[0] ?? "";
  if (!pathOnly.startsWith("/") || pathOnly.startsWith("//")) return false;
  if (pathOnly.includes("\\") || pathOnly.includes("://")) return false;
  const segments = pathOnly.split("/").filter(Boolean);
  if (segments.some((s) => s === ".." || s === ".")) return false;
  // Collapse accidental duplicate slashes for prefix check
  const normalized = "/" + segments.join("/");
  if (role) {
    return normalized === `/${role}` || normalized.startsWith(`/${role}/`);
  }
  return true;
}

export function safePortalRedirect(
  path: string | null | undefined,
  role: PortalRole,
): string {
  if (!isSafeInternalPath(path, role)) {
    return portalPath(role);
  }
  const pathOnly = decodeURIComponent(path).split(/[?#]/, 1)[0]!;
  const segments = pathOnly.split("/").filter(Boolean);
  return "/" + segments.join("/");
}

export async function readSessionId(): Promise<string | undefined> {
  const jar = await cookies();
  return jar.get(SESSION_COOKIE)?.value;
}

export async function setSessionCookie(sessionId: string): Promise<void> {
  const jar = await cookies();
  jar.set(SESSION_COOKIE, sessionId, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
}

export async function clearSessionCookie(): Promise<void> {
  const jar = await cookies();
  jar.delete(SESSION_COOKIE);
}

export async function getAuthSession(): Promise<AuthSession | null> {
  const sessionId = await readSessionId();
  if (!sessionId) return null;
  const identity = getIdentityClient();
  const resolved = await identity.resolveSession(sessionId);
  if (!resolved) return null;
  return {
    session: resolved.session,
    user: resolved.user,
    assignment: resolved.assignment,
    workspaces: resolved.user.assignments,
  };
}

export async function loginWithCredentials(
  email: string,
  password: string,
  requestedRole: PortalRole,
): Promise<LoginAttempt> {
  if (!email?.trim() || !password) {
    return { ok: false, code: "INVALID_INPUT", message: GENERIC_AUTH_FAILURE };
  }
  const identity = getIdentityClient();
  const result = await identity.login(email, password);
  if (!result.ok) {
    await clearSessionCookie();
    return { ok: false, code: result.code, message: GENERIC_AUTH_FAILURE };
  }

  const matched = result.workspaces.find((w) => w.role === requestedRole);
  if (!matched) {
    await identity.logout(result.session.session_id);
    await clearSessionCookie();
    return {
      ok: true,
      session: {
        session: result.session,
        user: result.user,
        assignment: result.user.assignments[0]!,
        workspaces: result.workspaces,
      },
      role_match: false,
      requested_role: requestedRole,
    };
  }

  const activated =
    (await identity.selectAssignment(
      result.session.session_id,
      matched.assignment_id,
    )) ?? result.session;

  await setSessionCookie(activated.session_id);
  return {
    ok: true,
    session: {
      session: activated,
      user: result.user,
      assignment: matched,
      workspaces: result.workspaces,
    },
    role_match: true,
    requested_role: requestedRole,
  };
}

export async function registerCustomerAccount(input: {
  email: string;
  display_name: string;
  password: string;
  language?: string;
  roles?: unknown;
  tenant_id?: unknown;
  subject_refs?: unknown;
}): Promise<
  | { ok: true; redirectTo: string }
  | { ok: false; code: string; message: string }
> {
  // Reject privileged client fields before any peer call.
  if (
    input.roles !== undefined ||
    input.tenant_id !== undefined ||
    input.subject_refs !== undefined
  ) {
    return {
      ok: false,
      code: "PRIVILEGED_FIELDS_REJECTED",
      message: "Registration rejected privileged fields",
    };
  }

  const safe = {
    email: input.email,
    display_name: input.display_name,
    password: input.password,
    language: input.language,
  };

  const identity = getIdentityClient();
  const result = await identity.registerCustomer(safe);
  if (!result.ok) {
    if (result.code === "PRIVILEGED_FIELDS_REJECTED") {
      return {
        ok: false,
        code: result.code,
        message: "Registration rejected privileged fields",
      };
    }
    if (result.code === "ALREADY_EXISTS") {
      return {
        ok: false,
        code: result.code,
        message: GENERIC_AUTH_FAILURE,
      };
    }
    return {
      ok: false,
      code: result.code,
      message: "Check name, email and password (min 8 characters).",
    };
  }
  await setSessionCookie(result.session.session_id);
  return { ok: true, redirectTo: portalPath("customer") };
}

export async function logoutCurrentSession(): Promise<void> {
  const sessionId = await readSessionId();
  if (sessionId) {
    await getIdentityClient().logout(sessionId);
  }
  await clearSessionCookie();
}

export function workspaceChoices(workspaces: WorkspaceAssignment[]): Array<{
  role: PortalRole;
  href: string;
  label: string;
}> {
  return workspaces.map((w) => ({
    role: w.role,
    href: portalPath(w.role),
    label: `${ROLE_LABELS[w.role]} — ${w.label}`,
  }));
}
