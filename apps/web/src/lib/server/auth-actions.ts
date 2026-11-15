"use server";

import { redirect } from "next/navigation";
import type { PortalRole } from "../../../tests/stubs/identity";
import { PeerError } from "@/domain/types";
import { getIdentityClient } from "./identity-client";
import {
  acceptInvitationAccount,
  loginWithCredentials,
  logoutCurrentSession,
  portalPath,
  readSessionId,
  registerCustomerAccount,
  safePortalRedirect,
  switchActiveAssignment,
} from "./auth";
import { requireRole } from "./authorization";

export type ActionResult =
  | { ok: true; redirectTo?: string }
  | {
      ok: false;
      message: string;
      workspaces?: Array<{ label: string; href: string }>;
    };

/** Challenge / password flows — may flag peerError for UI peer-error region. */
export type ChallengeActionResult =
  | { ok: true; message: string; sandbox_code?: string }
  | { ok: false; message: string; peerError?: boolean };

const FORGOT_GENERIC = "If an account exists for that email, reset instructions were sent.";
const SESSION_REQUIRED = "Sign in to continue this step.";

function truthyEnv(value: string | undefined): boolean {
  return value === "1" || value === "true" || value === "True" || value === "yes";
}

/** Server-only: IDENTITY_SANDBOX or SENTINEL_V1_SANDBOX (never NEXT_PUBLIC). */
function isIdentitySandbox(): boolean {
  return truthyEnv(process.env.IDENTITY_SANDBOX) || truthyEnv(process.env.SENTINEL_V1_SANDBOX);
}

function peerFailure(err: unknown, fallback: string): ChallengeActionResult {
  if (err instanceof PeerError) {
    return {
      ok: false,
      message: err.message || fallback,
      peerError: true,
    };
  }
  return { ok: false, message: fallback, peerError: true };
}

async function resolveSandboxCode(
  existing: string | undefined,
  fetchCode: () => Promise<{ code: string }>,
): Promise<string | undefined> {
  if (existing) return existing;
  if (!isIdentitySandbox()) return undefined;
  try {
    return (await fetchCode()).code;
  } catch {
    return undefined;
  }
}

export async function loginAction(
  _prev: ActionResult | null,
  formData: FormData,
): Promise<ActionResult> {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");
  const role = String(formData.get("role") ?? "") as PortalRole;
  const next = String(formData.get("next") ?? "");

  const allowed: PortalRole[] = ["customer", "merchant", "operator", "supervisor", "risk", "admin"];
  if (!allowed.includes(role)) {
    return { ok: false, message: "Unknown portal." };
  }

  const result = await loginWithCredentials(email, password, role);
  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  if (!result.role_match) {
    const workspaces = result.session.workspaces.map((w) => ({
      label: w.label,
      href: portalPath(w.role),
    }));
    return {
      ok: false,
      message: `This account does not have the ${role} workspace.`,
      workspaces,
    };
  }

  redirect(safePortalRedirect(next || null, role));
}

export async function registerCustomerAction(
  _prev: ActionResult | null,
  formData: FormData,
): Promise<ActionResult> {
  const payload: {
    email: string;
    display_name: string;
    password: string;
    language?: string;
    roles?: unknown;
    tenant_id?: unknown;
    subject_refs?: unknown;
  } = {
    email: String(formData.get("email") ?? ""),
    display_name: String(formData.get("display_name") ?? ""),
    password: String(formData.get("password") ?? ""),
    language: String(formData.get("language") ?? "en") || "en",
  };

  // Surface smuggled privileged fields so the stub can reject them.
  if (formData.has("roles")) {
    payload.roles = formData.get("roles");
  }
  if (formData.has("tenant_id")) {
    payload.tenant_id = formData.get("tenant_id");
  }
  if (formData.has("subject_refs")) {
    payload.subject_refs = formData.get("subject_refs");
  }

  const result = await registerCustomerAccount(payload);
  if (!result.ok) {
    return { ok: false, message: result.message };
  }
  redirect(result.redirectTo);
}

export async function logoutAction(): Promise<void> {
  await logoutCurrentSession();
  // Land on shared login. Avoid racing a protected-layout requireRole
  // re-fetch that would bounce an already-cleared session through loginPath.
  redirect("/login");
}

export async function acceptInvitationAction(
  _prev: ActionResult | null,
  formData: FormData,
): Promise<ActionResult> {
  const result = await acceptInvitationAccount({
    token: String(formData.get("token") ?? ""),
    email: String(formData.get("email") ?? ""),
    password: String(formData.get("password") ?? ""),
    display_name: String(formData.get("display_name") ?? "") || undefined,
  });
  if (!result.ok) {
    return { ok: false, message: result.message };
  }
  redirect(result.redirectTo);
}

export async function inviteStaffAction(
  _prev: ActionResult | null,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireRole("admin");
  const identity = getIdentityClient();
  const result = await identity.inviteStaff(session.session.session_id, {
    display_name: String(formData.get("display_name") ?? ""),
    work_email: String(formData.get("work_email") ?? ""),
    tenant_id: String(formData.get("tenant_id") ?? "tenant-demo"),
    role_id: String(formData.get("role_id") ?? ""),
    scope: {},
    reason: String(formData.get("reason") ?? ""),
    idempotency_key: String(formData.get("idempotency_key") ?? "") || undefined,
  });
  if (!result.ok) {
    return { ok: false, message: result.message };
  }
  redirect("/admin/users");
}

/** Switch active workspace assignment without signing out. */
export async function switchWorkspaceAction(formData: FormData): Promise<void> {
  const result = await switchActiveAssignment(String(formData.get("assignment_id") ?? ""));
  if (!result.ok) {
    redirect("/unauthorized");
  }
  redirect(result.redirectTo);
}

/**
 * Unauthenticated password forgot — calls IdentityClient directly.
 * BFF session proxy 401s without cookie; do not route through it.
 * Always returns the same generic message (no email enumeration).
 */
export async function forgotPasswordAction(
  _prev: ChallengeActionResult | null,
  formData: FormData,
): Promise<ChallengeActionResult> {
  const email = String(formData.get("email") ?? "").trim();
  if (!email) {
    return { ok: false, message: "Email is required." };
  }
  try {
    const client = getIdentityClient();
    const result = await client.forgotPassword(email);
    const token = process.env.IDENTITY_SANDBOX_TOKEN ?? "";
    const sandbox_code = await resolveSandboxCode(result.sandbox_code, async () => {
      if (!token) {
        throw new Error("no sandbox token");
      }
      return client.sandboxPasswordResetCode(email, token);
    });
    return {
      ok: true,
      message: FORGOT_GENERIC,
      ...(sandbox_code ? { sandbox_code } : {}),
    };
  } catch (err) {
    return peerFailure(err, "Could not start password reset. Try again later.");
  }
}

/**
 * Unauthenticated password reset — IdentityClient only (no session cookie).
 */
export async function resetPasswordAction(
  _prev: ChallengeActionResult | null,
  formData: FormData,
): Promise<ChallengeActionResult> {
  const email = String(formData.get("email") ?? "").trim();
  const code = String(formData.get("code") ?? "").trim();
  const new_password = String(formData.get("new_password") ?? "");
  if (!email || !code || !new_password) {
    return {
      ok: false,
      message: "Email, reset code, and new password are required.",
    };
  }
  if (new_password.length < 8) {
    return {
      ok: false,
      message: "Password must be at least 8 characters.",
    };
  }
  try {
    await getIdentityClient().resetPassword({ email, code, new_password });
    return {
      ok: true,
      message: "Password updated. Sign in with your new password.",
    };
  } catch (err) {
    if (err instanceof PeerError && err.httpStatus && err.httpStatus < 500) {
      return {
        ok: false,
        message:
          err.code === "INVALID_INPUT"
            ? "Password must be at least 8 characters."
            : "Invalid or expired reset code.",
      };
    }
    return peerFailure(err, "Could not reset password. Try again later.");
  }
}

export async function requestVerifyAction(
  _prev: ChallengeActionResult | null,
  _formData: FormData,
): Promise<ChallengeActionResult> {
  const sessionId = await readSessionId();
  if (!sessionId) {
    return { ok: false, message: SESSION_REQUIRED };
  }
  try {
    const client = getIdentityClient();
    const result = await client.requestVerify(sessionId);
    const sandbox_code = await resolveSandboxCode(result.sandbox_code, () =>
      client.sandboxLatestCode(sessionId, "email_verify"),
    );
    return {
      ok: true,
      message: "Verification code sent.",
      ...(sandbox_code ? { sandbox_code } : {}),
    };
  } catch (err) {
    return peerFailure(err, "Could not request verification.");
  }
}

export async function confirmVerifyAction(
  _prev: ChallengeActionResult | null,
  formData: FormData,
): Promise<ChallengeActionResult> {
  const sessionId = await readSessionId();
  if (!sessionId) {
    return { ok: false, message: SESSION_REQUIRED };
  }
  const code = String(formData.get("code") ?? "").trim();
  if (!code) {
    return { ok: false, message: "Verification code is required." };
  }
  try {
    await getIdentityClient().confirmVerify(sessionId, code);
    return { ok: true, message: "Email verified." };
  } catch (err) {
    if (err instanceof PeerError && err.httpStatus && err.httpStatus < 500) {
      return {
        ok: false,
        message:
          err.code === "UNAUTHORIZED" ? SESSION_REQUIRED : "Invalid or expired verification code.",
      };
    }
    return peerFailure(err, "Could not confirm verification.");
  }
}

export async function mfaChallengeAction(
  _prev: ChallengeActionResult | null,
  _formData: FormData,
): Promise<ChallengeActionResult> {
  const sessionId = await readSessionId();
  if (!sessionId) {
    return { ok: false, message: SESSION_REQUIRED };
  }
  try {
    const client = getIdentityClient();
    const result = await client.mfaChallenge(sessionId);
    const sandbox_code = await resolveSandboxCode(result.sandbox_code, () =>
      client.sandboxLatestCode(sessionId, "mfa"),
    );
    return {
      ok: true,
      message: "MFA challenge issued.",
      ...(sandbox_code ? { sandbox_code } : {}),
    };
  } catch (err) {
    return peerFailure(err, "Could not start MFA challenge.");
  }
}

export async function mfaVerifyAction(
  _prev: ChallengeActionResult | null,
  formData: FormData,
): Promise<ChallengeActionResult> {
  const sessionId = await readSessionId();
  if (!sessionId) {
    return { ok: false, message: SESSION_REQUIRED };
  }
  const code = String(formData.get("code") ?? "").trim();
  if (!code) {
    return { ok: false, message: "MFA code is required." };
  }
  try {
    await getIdentityClient().mfaVerify(sessionId, code);
    return { ok: true, message: "MFA verified." };
  } catch (err) {
    if (err instanceof PeerError && err.httpStatus && err.httpStatus < 500) {
      return {
        ok: false,
        message: err.code === "UNAUTHORIZED" ? SESSION_REQUIRED : "Invalid or expired MFA code.",
      };
    }
    return peerFailure(err, "Could not verify MFA.");
  }
}
