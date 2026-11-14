"use server";

import { redirect } from "next/navigation";
import type { PortalRole } from "../../../tests/stubs/identity";
import { getIdentityClient } from "./identity-client";
import {
  acceptInvitationAccount,
  loginWithCredentials,
  logoutCurrentSession,
  portalPath,
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

export async function loginAction(
  _prev: ActionResult | null,
  formData: FormData,
): Promise<ActionResult> {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");
  const role = String(formData.get("role") ?? "") as PortalRole;
  const next = String(formData.get("next") ?? "");

  const allowed: PortalRole[] = [
    "customer",
    "merchant",
    "operator",
    "supervisor",
    "risk",
    "admin",
  ];
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
  const result = await switchActiveAssignment(
    String(formData.get("assignment_id") ?? ""),
  );
  if (!result.ok) {
    redirect("/unauthorized");
  }
  redirect(result.redirectTo);
}
