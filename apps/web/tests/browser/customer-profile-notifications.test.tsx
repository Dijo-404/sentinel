import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProfilePanel } from "@/components/customer/profile-panel";
import { NotificationsPanel } from "@/components/customer/notifications-panel";
import { toPublicProfileUser } from "@/lib/identity-public";
import type { IdentityUser } from "../stubs/identity";

vi.mock("@/lib/server/customer-actions", () => ({
  patchProfileAction: vi.fn(async () => ({
    ok: true as const,
    message: "Profile updated.",
    user: {
      user_id: "u1",
      email: "customer@example.test",
      display_name: "Updated Customer",
      preferred_language: "es",
      account_status: "ACTIVE" as const,
      account_class: "customer" as const,
    },
  })),
  markNotificationReadAction: vi.fn(async () => ({
    ok: true as const,
    notification_id: "ntf-1",
    read_at: "2026-11-15T01:00:00Z",
  })),
}));

const SECRET_PASSWORD = "fixture-secret-password-never-leak";

const profileUser = {
  user_id: "u1",
  email: "customer@example.test",
  display_name: "Demo Customer",
  preferred_language: "en",
  account_status: "ACTIVE" as const,
  account_class: "customer" as const,
};

const notifications = [
  {
    notification_id: "ntf-1",
    title: "Welcome",
    body: "Your customer workspace is ready.",
    created_at: "2026-11-14T12:00:00Z",
    read_at: null as string | null,
  },
];

describe("customer profile + notifications", () => {
  it("toPublicProfileUser strips password", () => {
    const raw = {
      ...profileUser,
      password: SECRET_PASSWORD,
      assignments: [],
    } satisfies IdentityUser;
    const pub = toPublicProfileUser(raw);
    expect(pub).not.toHaveProperty("password");
    expect(JSON.stringify(pub)).not.toContain(SECRET_PASSWORD);
  });

  it("profile success shows me fields — no Not available yet", () => {
    const { container } = render(<ProfilePanel user={profileUser} />);

    expect(screen.getByTestId("customer-profile")).toBeInTheDocument();
    expect(screen.getByTestId("customer-profile-data")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Demo Customer")).toBeInTheDocument();
    expect(screen.getByText("customer@example.test")).toBeInTheDocument();
    expect(screen.getByDisplayValue("en")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(container.innerHTML).not.toContain(SECRET_PASSWORD);
    expect(container.innerHTML).not.toMatch(/"password"/);
  });

  it("profile HTML never includes password even if raw user sneaks in", () => {
    const sneaky = {
      ...profileUser,
      password: SECRET_PASSWORD,
    };
    const { container } = render(
      <ProfilePanel user={sneaky as typeof profileUser} />,
    );
    expect(container.innerHTML).not.toContain(SECRET_PASSWORD);
    expect(document.body.innerHTML).not.toContain(SECRET_PASSWORD);
  });

  it("profile peer failure shows peer-error — no stub copy", () => {
    render(
      <ProfilePanel
        error={{
          code: "PEER_UNAVAILABLE",
          message: "Identity peer unavailable",
        }}
      />,
    );

    expect(screen.getByTestId("customer-profile")).toBeInTheDocument();
    expect(screen.getByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByTestId("customer-profile-data")).not.toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });

  it("profile save updates via action — no password in HTML", async () => {
    const user = userEvent.setup();
    const { container } = render(<ProfilePanel user={profileUser} />);

    const name = screen.getByTestId("profile-display-name");
    await user.clear(name);
    await user.type(name, "Updated Customer");
    await user.click(screen.getByTestId("profile-save"));

    expect(await screen.findByTestId("profile-success")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(container.innerHTML).not.toContain(SECRET_PASSWORD);
    expect(container.innerHTML).not.toMatch(/"password"/);
  });

  it("profile peer failure on save shows peer-error — form stays", async () => {
    const { patchProfileAction } = await import(
      "@/lib/server/customer-actions"
    );
    vi.mocked(patchProfileAction).mockResolvedValueOnce({
      ok: false,
      message: "Identity peer unavailable",
      peerError: true,
    });
    const user = userEvent.setup();
    render(<ProfilePanel user={profileUser} />);
    await user.click(screen.getByTestId("profile-save"));

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.getByTestId("profile-save")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });

  it("notifications success lists inbox — no Not available yet", () => {
    render(<NotificationsPanel notifications={notifications} />);

    expect(screen.getByTestId("customer-notifications")).toBeInTheDocument();
    expect(screen.getByTestId("customer-notifications-list")).toBeInTheDocument();
    expect(screen.getByText("Welcome")).toBeInTheDocument();
    expect(
      screen.getByText("Your customer workspace is ready."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });

  it("notifications peer failure shows peer-error — no stub copy", () => {
    render(
      <NotificationsPanel
        error={{
          code: "PEER_UNAVAILABLE",
          message: "Identity peer unavailable",
        }}
      />,
    );

    expect(screen.getByTestId("customer-notifications")).toBeInTheDocument();
    expect(screen.getByTestId("peer-error")).toBeInTheDocument();
    expect(
      screen.queryByTestId("customer-notifications-list"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });

  it("mark notification read via action — no Not available yet", async () => {
    const user = userEvent.setup();
    render(<NotificationsPanel notifications={notifications} />);

    await user.click(screen.getByTestId("mark-read-ntf-1"));
    expect(await screen.findByTestId("notification-ntf-1-read")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });

  it("mark-read soft failure shows yellow warning — list stays", async () => {
    const { markNotificationReadAction } = await import(
      "@/lib/server/customer-actions"
    );
    vi.mocked(markNotificationReadAction).mockResolvedValueOnce({
      ok: false,
      message: "Notification not found",
    });
    const user = userEvent.setup();
    render(<NotificationsPanel notifications={notifications} />);
    await user.click(screen.getByTestId("mark-read-ntf-1"));

    const banner = await screen.findByTestId("notification-error");
    expect(banner).toHaveAttribute("data-tone", "warning");
    expect(banner).toHaveTextContent("Notification not found");
    expect(screen.getByTestId("customer-notifications-list")).toBeInTheDocument();
    expect(screen.queryByTestId("peer-error")).not.toBeInTheDocument();
  });
});
