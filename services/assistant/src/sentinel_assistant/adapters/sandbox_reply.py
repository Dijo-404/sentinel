"""Sandbox reply generator: input-dependent, explicitly labeled, no model call."""

from __future__ import annotations


class SandboxEchoReply:
    """Honest sandbox assistant — reply content depends on user text; not a live model."""

    def generate(self, *, text: str) -> tuple[str, str]:
        excerpt = (text or "").strip()
        if len(excerpt) > 160:
            excerpt = f"{excerpt[:157]}..."
        body = (
            f"Sandbox assistant reply for: {excerpt}. "
            "Models propose only; no payment or ledger authority."
        )
        return body, "sandbox"
