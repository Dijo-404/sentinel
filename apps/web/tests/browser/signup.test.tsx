import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CustomerRegisterForm } from "@/components/auth/customer-register";
import { registerCustomerAction, registerMerchantAction } from "@/lib/server/auth-actions";

vi.mock("@/lib/server/auth-actions", () => ({
  registerCustomerAction: vi.fn(async () => ({ ok: false, message: "Customer response" })),
  registerMerchantAction: vi.fn(async () => ({ ok: false, message: "Merchant response" })),
}));

describe("public signup", () => {
  it("prefills email and exposes only customer and merchant tabs with keyboard navigation", async () => {
    const user = userEvent.setup();
    render(<CustomerRegisterForm email="new+person@example.test" />);
    expect(screen.getByLabelText("Email")).toHaveValue("new+person@example.test");
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual(["Customer", "Merchant"]);
    expect(screen.getByRole("tablist")).toHaveAccessibleName("Account type");
    tabs[0]!.focus();
    await user.keyboard("{ArrowRight}");
    expect(tabs[1]).toHaveFocus();
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveAccessibleName("Merchant");
    expect(screen.getByLabelText("Business name")).toBeRequired();
    await user.keyboard("{ArrowRight}");
    expect(tabs[0]).toHaveFocus();
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{End}");
    expect(tabs[1]).toHaveFocus();
    await user.keyboard("{Home}");
    expect(tabs[0]).toHaveFocus();
    expect(screen.queryByLabelText("Business name")).not.toBeInTheDocument();
  });

  it.each(["customer", "merchant"] as const)(
    "submits %s signup through the corresponding action",
    async (type) => {
      const user = userEvent.setup();
      render(<CustomerRegisterForm accountType={type} />);
      await user.type(screen.getByLabelText("Full name"), "New User");
      await user.type(screen.getByLabelText("Email"), "new@example.test");
      await user.type(screen.getByLabelText("Password (min 8 characters)"), "password1");
      if (type === "merchant")
        await user.type(screen.getByLabelText("Business name"), "Sandbox Shop");
      await user.click(screen.getByRole("checkbox"));
      await user.click(screen.getByTestId("register-submit"));
      const action = type === "merchant" ? registerMerchantAction : registerCustomerAction;
      await waitFor(() => expect(action).toHaveBeenCalled());
      expect(await screen.findByRole("alert")).toHaveTextContent(
        type === "merchant" ? "Merchant response" : "Customer response",
      );
    },
  );
});
