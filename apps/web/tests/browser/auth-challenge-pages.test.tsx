import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WorkspacePicker } from "@/components/auth/workspace-picker";
import { VerifyContactForm } from "@/components/auth/verify-contact-form";
import { MfaChallengeForm } from "@/components/auth/mfa-challenge-form";
import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

vi.mock("@/lib/server/auth-actions", () => ({
  switchWorkspaceAction: vi.fn(),
  forgotPasswordAction: vi.fn(async () => ({
    ok: true as const,
    message: "If an account exists for that email, reset instructions were sent.",
  })),
  resetPasswordAction: vi.fn(async () => ({
    ok: true as const,
    message: "Password updated. Sign in with your new password.",
  })),
  requestVerifyAction: vi.fn(async () => ({
    ok: true as const,
    message: "Verification code sent.",
    sandbox_code: "fixture-verify",
  })),
  confirmVerifyAction: vi.fn(async () => ({
    ok: true as const,
    message: "Email verified.",
  })),
  mfaChallengeAction: vi.fn(async () => ({
    ok: true as const,
    message: "MFA challenge issued.",
    sandbox_code: "MFA1234",
  })),
  mfaVerifyAction: vi.fn(async () => ({
    ok: true as const,
    message: "MFA verified.",
  })),
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("email=customer@example.test"),
}));

describe("auth challenge pages", () => {
  it("workspaces success lists assignments — no Fixture placeholder", () => {
    render(
      <WorkspacePicker
        workspaces={[
          {
            assignment_id: "a1",
            role: "customer",
            label: "Customer — Personal",
          },
          {
            assignment_id: "a2",
            role: "merchant",
            label: "Merchant — Demo",
          },
        ]}
        activeAssignmentId="a1"
      />,
    );

    expect(screen.getByTestId("auth-workspaces")).toBeInTheDocument();
    expect(screen.getByTestId("auth-workspaces-list")).toBeInTheDocument();
    expect(screen.getByTestId("select-workspace-a1")).toBeInTheDocument();
    expect(screen.getByTestId("select-workspace-a2")).toBeInTheDocument();
    expect(screen.getByText(/Customer — Personal/)).toBeInTheDocument();
    expect(screen.getByText(/Merchant — Demo/)).toBeInTheDocument();
    expect(screen.queryByText("Fixture placeholder")).not.toBeInTheDocument();
  });

  it("workspaces peer failure shows peer-error — no Fixture placeholder", () => {
    render(
      <WorkspacePicker
        workspaces={[]}
        error={{ code: "PEER_UNAVAILABLE", message: "Identity peer unavailable" }}
      />,
    );

    expect(screen.getByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByTestId("auth-workspaces-list")).not.toBeInTheDocument();
    expect(screen.queryByText("Fixture placeholder")).not.toBeInTheDocument();
  });

  it("verify success region after request — no Fixture placeholder", async () => {
    const user = userEvent.setup();
    render(<VerifyContactForm />);

    expect(screen.getByTestId("auth-verify")).toBeInTheDocument();
    expect(screen.queryByText("Fixture placeholder")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("verify-request"));
    expect(await screen.findByTestId("verify-success")).toBeInTheDocument();
  });

  it("verify request SESSION_REQUIRED surfaces verify-error — forms stay", async () => {
    const { requestVerifyAction } = await import("@/lib/server/auth-actions");
    vi.mocked(requestVerifyAction).mockResolvedValueOnce({
      ok: false,
      message: "Sign in to continue this step.",
    });
    const user = userEvent.setup();
    render(<VerifyContactForm />);
    await user.click(screen.getByTestId("verify-request"));
    expect(await screen.findByTestId("verify-error")).toHaveTextContent(
      "Sign in to continue this step.",
    );
    expect(screen.getByTestId("verify-request")).toBeInTheDocument();
    expect(screen.getByTestId("verify-confirm")).toBeInTheDocument();
  });

  it("verify peer failure shows peer-error and keeps forms", async () => {
    const { requestVerifyAction } = await import("@/lib/server/auth-actions");
    vi.mocked(requestVerifyAction).mockResolvedValueOnce({
      ok: false,
      message: "Identity peer unavailable",
      peerError: true,
    });
    const user = userEvent.setup();
    render(<VerifyContactForm />);
    await user.click(screen.getByTestId("verify-request"));
    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.getByTestId("verify-request")).toBeInTheDocument();
    expect(screen.getByTestId("verify-confirm")).toBeInTheDocument();
    expect(screen.queryByText("Fixture placeholder")).not.toBeInTheDocument();
  });

  it("mfa success region after challenge — no Fixture placeholder", async () => {
    const user = userEvent.setup();
    render(<MfaChallengeForm />);

    expect(screen.getByTestId("auth-mfa")).toBeInTheDocument();
    expect(screen.queryByText("Fixture placeholder")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("mfa-challenge"));
    expect(await screen.findByTestId("mfa-success")).toBeInTheDocument();
  });

  it("mfa challenge SESSION_REQUIRED surfaces mfa-error — forms stay", async () => {
    const { mfaChallengeAction } = await import("@/lib/server/auth-actions");
    vi.mocked(mfaChallengeAction).mockResolvedValueOnce({
      ok: false,
      message: "Sign in to continue this step.",
    });
    const user = userEvent.setup();
    render(<MfaChallengeForm />);
    await user.click(screen.getByTestId("mfa-challenge"));
    expect(await screen.findByTestId("mfa-error")).toHaveTextContent(
      "Sign in to continue this step.",
    );
    expect(screen.getByTestId("mfa-challenge")).toBeInTheDocument();
    expect(screen.getByTestId("mfa-verify")).toBeInTheDocument();
  });

  it("mfa peer failure shows peer-error and keeps forms", async () => {
    const { mfaChallengeAction } = await import("@/lib/server/auth-actions");
    vi.mocked(mfaChallengeAction).mockResolvedValueOnce({
      ok: false,
      message: "Identity peer unavailable",
      peerError: true,
    });
    const user = userEvent.setup();
    render(<MfaChallengeForm />);
    await user.click(screen.getByTestId("mfa-challenge"));
    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.getByTestId("mfa-challenge")).toBeInTheDocument();
    expect(screen.getByTestId("mfa-verify")).toBeInTheDocument();
    expect(screen.queryByText("Fixture placeholder")).not.toBeInTheDocument();
  });

  it("forgot password success — no Fixture placeholder, no invented email body", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    expect(screen.getByTestId("auth-forgot")).toBeInTheDocument();
    expect(screen.queryByText("Fixture placeholder")).not.toBeInTheDocument();

    await user.type(screen.getByTestId("forgot-email"), "customer@example.test");
    await user.click(screen.getByTestId("forgot-submit"));
    expect(await screen.findByTestId("forgot-success")).toBeInTheDocument();
    expect(screen.queryByText(/Dear customer/i)).not.toBeInTheDocument();
  });

  it("reset password success — no Fixture placeholder", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordForm />);

    expect(screen.getByTestId("auth-reset")).toBeInTheDocument();
    expect(screen.queryByText("Fixture placeholder")).not.toBeInTheDocument();

    await user.type(screen.getByTestId("reset-code"), "fixture-reset");
    await user.type(screen.getByTestId("reset-password"), "new-password-9");
    await user.click(screen.getByTestId("reset-submit"));
    expect(await screen.findByTestId("reset-success")).toBeInTheDocument();
  });
});
