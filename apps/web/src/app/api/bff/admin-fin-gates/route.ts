import { NextResponse } from "next/server";
import { getAuthSession } from "@/lib/server/auth";
import { projectAdminFinGates } from "@/lib/server/fin-gates";

/** Admin-only FinHarness/FinBench gate projection. No invented live scores. */
export async function GET() {
  let session;
  try {
    session = await getAuthSession();
  } catch {
    return NextResponse.json(
      {
        code: "PEER_UNAVAILABLE",
        message: "Identity unavailable",
        request_id: "web-bff-fin-gates-peer",
      },
      { status: 503 },
    );
  }
  if (!session) {
    return NextResponse.json(
      {
        code: "UNAUTHORIZED",
        message: "Missing sentinel_session; sign in required",
        request_id: "web-bff-fin-gates-unauth",
      },
      { status: 401 },
    );
  }
  if (session.assignment.role !== "admin") {
    return NextResponse.json(
      {
        code: "FORBIDDEN",
        message: "Platform admin role required",
        request_id: "web-bff-fin-gates-denied",
      },
      { status: 403 },
    );
  }
  return NextResponse.json(projectAdminFinGates(), { status: 200 });
}
