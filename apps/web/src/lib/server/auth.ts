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

export function isSafeInternalPath(path: string | null | undefined): path is string {
  if (!path || !path.startsWith("/") || path.startsWith("//")) return false;
  if (path.includes("://") || path.includes("\\")) return false;
  return true;
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
  const resolved = identity.resolveSession(sessionId);
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
  const result = identity.login(email, password);
  if (!result.ok) {
    return { ok: false, code: result.code, message: GENERIC_AUTH_FAILURE };
  }
  await setSessionCookie(result.session.session_id);
  const role_match = result.workspaces.some((w) => w.role === requestedRole);
  return {
    ok: true,
    session: {
      session: result.session,
      user: result.user,
      assignment: result.workspaces.find((w) => w.role === requestedRole) ??
        result.user.assignments[0]!,
      workspaces: result.workspaces,
    },
    role_match,
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
  const identity = getIdentityClient();
  const result = identity.registerCustomer(input);
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
    getIdentityClient().logout(sessionId);
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
