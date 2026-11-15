import { timingSafeEqual } from "node:crypto";
import { isIP } from "node:net";
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

/** Default cookie lifetime aligned with identity SESSION_TTL (~12h). */
export const SESSION_COOKIE_MAX_AGE_SECONDS = 12 * 60 * 60;

export type AuthSession = {
  session: SessionRecord;
  user: IdentityUser;
  assignment: WorkspaceAssignment;
  workspaces: WorkspaceAssignment[];
};

export type LoginAttempt =
  | { ok: true; session: AuthSession; redirectTo: string }
  | { ok: false; code: string; message: string };

/** Next actions expose no transport address; authenticate an explicitly configured ingress. */
export function trustedLoginClientIp(
  incoming: Pick<Headers, "get">,
  env: Record<string, string | undefined> = process.env,
): string | undefined {
  const expected = env.WEB_TRUSTED_INGRESS_TOKEN;
  const supplied = incoming.get("x-sentinel-ingress-token");
  if (!expected || expected.length < 32 || !supplied) return undefined;
  const a = Buffer.from(expected);
  const b = Buffer.from(supplied);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return undefined;
  const ip = incoming.get("x-sentinel-client-ip");
  return ip && isIP(ip) ? ip : undefined;
}

const REGISTER_FAILURE =
  "We couldn't create this account. Check your name, email and password (min 8 characters), or sign in if you already have an account.";

const GENERIC_AUTH_FAILURE = "Sign-in failed. Check your credentials and try again.";

export function portalPath(role: PortalRole): string {
  return `/${role}/dashboard`;
}

export function loginPath(role: PortalRole): string {
  return `/login?portal=${role}`;
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

export function safePortalRedirect(path: string | null | undefined, role: PortalRole): string {
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

export function cookieMaxAgeSeconds(expiresAt?: string | null): number {
  if (expiresAt) {
    const ms = Date.parse(expiresAt) - Date.now();
    if (Number.isFinite(ms) && ms > 0) {
      return Math.floor(ms / 1000);
    }
  }
  return SESSION_COOKIE_MAX_AGE_SECONDS;
}

export async function setSessionCookie(
  sessionId: string,
  expiresAt?: string | null,
): Promise<void> {
  const jar = await cookies();
  jar.set(SESSION_COOKIE, sessionId, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: cookieMaxAgeSeconds(expiresAt),
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
  clientIp?: string,
): Promise<LoginAttempt> {
  if (!email?.trim() || !password) {
    return { ok: false, code: "INVALID_INPUT", message: GENERIC_AUTH_FAILURE };
  }
  const identity = getIdentityClient();
  let provisional: string | undefined;
  try {
    const result = await identity.login(email, password, clientIp);
    if (!result.ok) {
      await clearSessionCookie();
      return { ok: false, code: result.code, message: GENERIC_AUTH_FAILURE };
    }
    provisional = result.session.session_id;
    const { workspaces } = await identity.listWorkspaces(provisional);
    const assignment = workspaces[0];
    if (!assignment) throw new Error("No authorized workspaces");
    const session =
      workspaces.length === 1
        ? await identity.selectAssignment(provisional, assignment.assignment_id)
        : result.session;
    if (!session) throw new Error("Workspace selection failed");
    await setSessionCookie(session.session_id, session.expires_at);
    return {
      ok: true,
      redirectTo: workspaces.length === 1 ? portalPath(assignment.role) : "/auth/workspaces",
      session: { session, user: result.user, assignment, workspaces },
    };
  } catch {
    if (provisional) {
      try {
        await identity.logout(provisional);
      } catch {
        /* Peer unavailable; never retain the cookie. */
      }
    }
    await clearSessionCookie();
    return {
      ok: false,
      code: "PEER_UNAVAILABLE",
      message: "Sign-in is unavailable. Try again later.",
    };
  }
}

type RegistrationInput = {
  email: string;
  display_name: string;
  password: string;
  language?: string;
  roles?: unknown;
  tenant_id?: unknown;
  subject_refs?: unknown;
  business_name?: string;
  merchant_ref?: unknown;
  subject_ref?: unknown;
  role_id?: unknown;
  account_type?: unknown;
};

export async function registerCustomerAccount(input: RegistrationInput) {
  return registerAccount(input, "customer");
}

export async function registerMerchantAccount(
  input: RegistrationInput & { business_name: string },
) {
  return registerAccount(input, "merchant");
}

async function registerAccount(
  input: RegistrationInput,
  type: "customer" | "merchant",
): Promise<{ ok: true; redirectTo: string } | { ok: false; code: string; message: string }> {
  // Reject privileged client fields before any peer call.
  if (
    input.roles !== undefined ||
    input.tenant_id !== undefined ||
    input.subject_refs !== undefined ||
    input.merchant_ref !== undefined ||
    input.subject_ref !== undefined ||
    input.role_id !== undefined ||
    input.account_type !== undefined
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
  const result =
    type === "merchant"
      ? await identity.registerMerchant({ ...safe, business_name: input.business_name ?? "" })
      : await identity.registerCustomer(safe);
  if (!result.ok) {
    if (result.code === "PRIVILEGED_FIELDS_REJECTED") {
      return {
        ok: false,
        code: result.code,
        message: "Registration rejected privileged fields",
      };
    }
    // Same text for ALREADY_EXISTS and invalid input: the reply must not reveal registered emails.
    return {
      ok: false,
      code: result.code,
      message: REGISTER_FAILURE,
    };
  }
  await setSessionCookie(result.session.session_id, result.session.expires_at);
  return { ok: true, redirectTo: portalPath(type) };
}

export async function acceptInvitationAccount(input: {
  token: string;
  email: string;
  password: string;
  display_name?: string;
}): Promise<
  { ok: true; redirectTo: string; role: PortalRole } | { ok: false; code: string; message: string }
> {
  const token = input.token?.trim() ?? "";
  const email = input.email?.trim() ?? "";
  const password = input.password ?? "";
  if (!token || !email || !password) {
    return {
      ok: false,
      code: "INVALID_INPUT",
      message: "Invitation token, email and password are required.",
    };
  }
  if (password.length < 8) {
    return {
      ok: false,
      code: "INVALID_INPUT",
      message: "Check name, email and password (min 8 characters).",
    };
  }

  const identity = getIdentityClient();
  const result = await identity.acceptInvitation({
    token,
    email,
    password,
    display_name: input.display_name,
  });
  if (!result.ok) {
    await clearSessionCookie();
    return {
      ok: false,
      code: result.code,
      message:
        result.code === "INVALID_INPUT"
          ? "Check name, email and password (min 8 characters)."
          : GENERIC_AUTH_FAILURE,
    };
  }

  await setSessionCookie(result.session.session_id, result.session.expires_at);
  return {
    ok: true,
    redirectTo: portalPath(result.assignment.role),
    role: result.assignment.role,
  };
}

export async function logoutCurrentSession(): Promise<void> {
  const sessionId = await readSessionId();
  if (sessionId) {
    await getIdentityClient().logout(sessionId);
  }
  await clearSessionCookie();
}

/**
 * Bind the current session to another assignment the user already holds.
 * Updates the httpOnly cookie (real-peer may mint a new session_token).
 */
export async function switchActiveAssignment(
  assignmentId: string,
): Promise<{ ok: true; role: PortalRole; redirectTo: string } | { ok: false; message: string }> {
  const trimmed = assignmentId?.trim() ?? "";
  if (!trimmed) {
    return { ok: false, message: "Workspace assignment is required." };
  }
  const sessionId = await readSessionId();
  if (!sessionId) return { ok: false, message: "Sign in to switch workspace." };
  const identity = getIdentityClient();
  // An authenticated login may have no active assignment until this selection.
  const listed = await identity.listWorkspaces(sessionId);
  const target = listed.workspaces.find((w) => w.assignment_id === trimmed);
  if (!target) return { ok: false, message: "That workspace is not available." };
  const activated = await identity.selectAssignment(sessionId, trimmed);
  if (!activated) {
    return { ok: false, message: "Could not switch workspace." };
  }
  await setSessionCookie(activated.session_id, activated.expires_at);
  return {
    ok: true,
    role: target.role,
    redirectTo: portalPath(target.role),
  };
}

export function workspaceChoices(workspaces: WorkspaceAssignment[]): Array<{
  assignment_id: string;
  role: PortalRole;
  href: string;
  label: string;
}> {
  return workspaces.map((w) => ({
    assignment_id: w.assignment_id,
    role: w.role,
    href: portalPath(w.role),
    label: `${ROLE_LABELS[w.role]} — ${w.label}`,
  }));
}
