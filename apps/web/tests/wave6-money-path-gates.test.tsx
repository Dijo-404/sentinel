/**
 * Wave 6 money-path composition gates (portal assembly).
 * Dedicated file so wave6 CI/PR evidence pins these invariants in one place.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { loadShellConfig } from "@/adapters/composition";
import { PeerError } from "@/domain/types";
import { ApprovalSlot } from "@/slots/approval-slot";
import { LocalVoiceSubstitute } from "@/slots/local-voice-substitute";
import { createApprovalUiStub } from "./stubs/approval-ui";

describe("wave6 money-path gates", () => {
  it("default composition mode is real-peers (loadShellConfig({}))", () => {
    const config = loadShellConfig({});
    expect(config.mode).toBe("real-peers");
  });

  it("ApprovalSlot real-peers does not set approval-ui.v1-local data-slot", () => {
    const ok = createApprovalUiStub("valid");
    expect(ok.status).toBe("ok");
    if (ok.status !== "ok") return;
    render(
      <ApprovalSlot
        state="ready"
        props={ok.props}
        mode="real-peers"
        reviewerId="supervisor-demo-1"
        now={() => new Date("2026-11-13T12:00:00Z")}
      />,
    );
    expect(
      document.querySelector('[data-slot="approval-ui.v1-local"]'),
    ).toBeNull();
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
    expect(
      screen.queryByText(/local substitute/i),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Approval required" }),
    ).toBeInTheDocument();
  });

  it("voice enabled path fails closed on peer down (no fake transcript)", async () => {
    const user = userEvent.setup();
    render(
      <LocalVoiceSubstitute
        enabled
        client={{
          async transcribe() {
            throw new PeerError("PEER_UNAVAILABLE", "down", "v1", 503);
          },
        }}
      />,
    );
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Transcribe" }));
    expect(await screen.findByTestId("voice-slot-error")).toHaveTextContent(
      "PEER_UNAVAILABLE",
    );
    expect(screen.queryByTestId("voice-slot-result")).not.toBeInTheDocument();
  });
});
