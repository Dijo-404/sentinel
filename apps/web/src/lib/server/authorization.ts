import { redirect } from "next/navigation";
import type { PortalRole } from "../../../tests/stubs/identity";
import { getAuthSession, loginPath, portalPath, type AuthSession, workspaceChoices } from "./auth";

export type RequireRoleResult =
  | { ok: true; session: AuthSession }
  | {
      ok: false;
      reason: "unauthenticated" | "role_mismatch";
      loginHref: string;
      unauthorizedHref: string;
      workspaces: ReturnType<typeof workspaceChoices>;
    };

export async function checkRole(required: PortalRole): Promise<RequireRoleResult> {
  const session = await getAuthSession();
  const loginHref = loginPath(required);
  if (!session) {
    return {
      ok: false,
      reason: "unauthenticated",
      loginHref,
      unauthorizedHref: `/unauthorized?portal=${required}`,
      workspaces: [],
    };
  }
  // Active assignment only — holding another workspace is not enough.
  if (session.assignment.role !== required) {
    return {
      ok: false,
      reason: "role_mismatch",
      loginHref,
      unauthorizedHref: `/unauthorized?portal=${required}`,
      workspaces: workspaceChoices(session.workspaces),
    };
  }
  return { ok: true, session };
}

/** Convenience redirect for protected layouts. Not the sole auth barrier. */
export async function requireRole(required: PortalRole): Promise<AuthSession> {
  const result = await checkRole(required);
  if (!result.ok) {
    if (result.reason === "unauthenticated") {
      redirect(result.loginHref);
    }
    redirect(result.unauthorizedHref);
  }
  return result.session;
}

/**
 * Accept any of the listed roles on the *active* assignment.
 * Unauthenticated users go to `loginAs` login.
 */
export async function requireAnyRole(
  allowed: PortalRole[],
  loginAs: PortalRole = allowed[0]!,
): Promise<AuthSession> {
  const session = await getAuthSession();
  if (!session) {
    redirect(loginPath(loginAs));
  }
  if (!allowed.includes(session.assignment.role)) {
    redirect(`/unauthorized?portal=${loginAs}`);
  }
  return session;
}

export function dashboardFor(role: PortalRole): string {
  return portalPath(role);
}
