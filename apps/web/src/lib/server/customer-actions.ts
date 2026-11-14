"use server";

import type { IdentityUser } from "../../../tests/stubs/identity";
import { PeerError } from "@/domain/types";
import { readSessionId } from "./auth";
import { getIdentityClient } from "./identity-client";

export type ProfileActionResult =
  | { ok: true; message: string; user: IdentityUser }
  | { ok: false; message: string; peerError?: boolean };

export type MarkReadActionResult =
  | { ok: true; notification_id: string; read_at: string }
  | { ok: false; message: string; peerError?: boolean };

const SESSION_REQUIRED = "Sign in to continue this step.";

function peerFailure(err: unknown, fallback: string): {
  ok: false;
  message: string;
  peerError: true;
} {
  if (err instanceof PeerError) {
    return {
      ok: false,
      message: err.message || fallback,
      peerError: true,
    };
  }
  return { ok: false, message: fallback, peerError: true };
}

export async function patchProfileAction(
  _prev: ProfileActionResult | null,
  formData: FormData,
): Promise<ProfileActionResult> {
  const sessionId = await readSessionId();
  if (!sessionId) {
    return { ok: false, message: SESSION_REQUIRED };
  }
  const display_name = String(formData.get("display_name") ?? "").trim();
  const preferred_language = String(
    formData.get("preferred_language") ?? "",
  ).trim();
  if (!display_name) {
    return { ok: false, message: "Display name is required." };
  }
  try {
    const result = await getIdentityClient().patchProfile(sessionId, {
      display_name,
      preferred_language: preferred_language || undefined,
    });
    return {
      ok: true,
      message: "Profile updated.",
      user: result.user,
    };
  } catch (err) {
    if (err instanceof PeerError && err.httpStatus && err.httpStatus < 500) {
      return {
        ok: false,
        message:
          err.code === "UNAUTHORIZED"
            ? SESSION_REQUIRED
            : err.message || "Could not update profile.",
      };
    }
    return peerFailure(err, "Could not update profile.");
  }
}

export async function markNotificationReadAction(
  _prev: MarkReadActionResult | null,
  formData: FormData,
): Promise<MarkReadActionResult> {
  const sessionId = await readSessionId();
  if (!sessionId) {
    return { ok: false, message: SESSION_REQUIRED };
  }
  const notificationId = String(formData.get("notification_id") ?? "").trim();
  if (!notificationId) {
    return { ok: false, message: "Notification id is required." };
  }
  try {
    const result = await getIdentityClient().markNotificationRead(
      sessionId,
      notificationId,
    );
    return {
      ok: true,
      notification_id: result.notification_id,
      read_at: result.read_at,
    };
  } catch (err) {
    if (err instanceof PeerError && err.httpStatus && err.httpStatus < 500) {
      return {
        ok: false,
        message:
          err.code === "UNAUTHORIZED"
            ? SESSION_REQUIRED
            : err.message || "Could not mark notification read.",
      };
    }
    return peerFailure(err, "Could not mark notification read.");
  }
}
