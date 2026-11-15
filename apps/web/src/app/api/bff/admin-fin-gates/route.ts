import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { SESSION_COOKIE } from "@/lib/server/auth";
import { projectAdminFinGates } from "@/lib/server/fin-gates";

/** Admin-only FinHarness/FinBench gate projection. No invented live scores. */
export async function GET() {
  const jar = await cookies();
  if (!jar.get(SESSION_COOKIE)?.value) {
    return NextResponse.json(
      {
        code: "UNAUTHORIZED",
        message: "Missing sentinel_session; sign in required",
        request_id: "web-bff-fin-gates-unauth",
      },
      { status: 401 },
    );
  }
  return NextResponse.json(projectAdminFinGates(), { status: 200 });
}
