import { afterEach, describe, expect, it, vi } from "vitest";
vi.mock("@/lib/server/auth", () => ({ getAuthSession: vi.fn() }));
import { getAuthSession } from "@/lib/server/auth";
import { GET } from "@/app/api/bff/admin-fin-gates/route";
afterEach(() => vi.clearAllMocks());
describe("admin gate authorization", () => {
  it.each([
    [null, 401],
    ["customer", 403],
    ["operator", 403],
    ["admin", 200],
  ] as const)("checks live identity assignment %s", async (role, status) => {
    vi.mocked(getAuthSession).mockResolvedValue(
      role ? ({ assignment: { role } } as Awaited<ReturnType<typeof getAuthSession>>) : null,
    );
    expect((await GET()).status).toBe(status);
  });
  it("fails closed when identity is unavailable", async () => {
    vi.mocked(getAuthSession).mockRejectedValueOnce(new Error("offline"));
    expect((await GET()).status).toBe(503);
  });
});
