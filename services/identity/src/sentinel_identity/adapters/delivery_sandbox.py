"""Sandbox invitation delivery: drain durable outbox into local inbox links."""

from __future__ import annotations

from urllib.parse import quote

from ..application.ports import Clock, IdentityStore

DEFAULT_ACCEPT_LINK_BASE = "http://127.0.0.1:3000"


class SandboxDeliveryAdapter:
    """In-module delivery consumer. No production email provider."""

    def __init__(
        self,
        store: IdentityStore,
        clock: Clock,
        *,
        accept_link_base: str = DEFAULT_ACCEPT_LINK_BASE,
    ) -> None:
        self._store = store
        self._clock = clock
        self._accept_link_base = accept_link_base.rstrip("/")

    def build_acceptance_link(self, raw_token: str) -> str:
        return f"{self._accept_link_base}/auth/accept-invitation?token={quote(raw_token, safe='')}"

    def drain(self) -> int:
        """Move pending outbox rows into sandbox inbox with acceptance links."""
        pending = self._store.list_pending_deliveries()
        now = self._clock.now()
        delivered = 0
        for item in pending:
            link = self.build_acceptance_link(item.raw_token)
            self._store.mark_delivery_delivered(item.delivery_id, acceptance_link=link, at=now)
            delivered += 1
        return delivered
