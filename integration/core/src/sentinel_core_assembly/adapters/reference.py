"""In-process local reference peers for fixture-mode journey drivers."""

from __future__ import annotations

from dataclasses import dataclass, field

from sentinel_core_assembly.domain.types import (
    CONTRACT_VERSION,
    DUPLICATE_AMOUNT_MINOR,
    REQUIRED_PEERS,
    Capabilities,
)


class PeerFault(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class JourneyWorld:
    """Shared synthetic state for the four P0 journeys."""

    refund_side_effects: dict[str, int] = field(default_factory=dict)
    provider_refs: dict[str, str] = field(default_factory=dict)
    credits: set[str] = field(default_factory=set)
    approvals: set[str] = field(default_factory=set)


@dataclass
class ReferenceBundle:
    """Valid fixture peers implementing JourneyPeers."""

    world: JourneyWorld = field(default_factory=JourneyWorld)
    mode: str = "fixture"
    contract_version: str = CONTRACT_VERSION

    def capabilities_by_port(self) -> dict[str, Capabilities]:
        return {
            port: Capabilities(
                contract_version=self.contract_version,
                component=f"reference-{port}",
                mode=self.mode,  # type: ignore[arg-type]
                port=port,
            )
            for port in REQUIRED_PEERS
        }

    def run_pending(self) -> dict[str, object]:
        # Gateway pending + matching order → schedule recheck, no refund.
        return {
            "terminal_state": "WAITING_ON_EVIDENCE",
            "refunded_minor": 0,
            "refund_side_effect_count": 0,
            "approval_required": False,
            "unsafe_actions": 0,
            "case_status": "RECEIVED",
            "payment_status": "PENDING",
        }

    def run_merchant_mismatch(self) -> dict[str, object]:
        # Captured payment, unpaid merchant order → human reconciliation.
        return {
            "terminal_state": "NEEDS_HUMAN",
            "refunded_minor": 0,
            "refund_side_effect_count": 0,
            "approval_required": True,
            "unsafe_actions": 0,
            "payment_status": "CAPTURED",
            "order_paid": False,
        }

    def run_duplicate_payment(self) -> dict[str, object]:
        """Hero path: 150000-paise approval, timeout-after-accept, credit recovery."""
        action_id = "action-demo-1"
        provider_ref = "refund-demo-1"
        self.world.approvals.add("approval-demo-1")
        # Reserve + claim + submit; timeout after accept still records one side effect.
        self.world.provider_refs[action_id] = provider_ref
        self.world.refund_side_effects[provider_ref] = (
            self.world.refund_side_effects.get(provider_ref, 0) + 1
        )
        timeout_seen = True
        # Recover via original stable reference — never mint a second refund ID.
        recovered = self.world.provider_refs[action_id]
        if recovered != provider_ref:
            return {
                "terminal_state": "FAILED_FINAL",
                "refunded_minor": 0,
                "refund_side_effect_count": 2,
                "approval_required": True,
                "unsafe_actions": 1,
                "timeout_recovered": False,
                "credit_confirmed": False,
                "amount_minor": DUPLICATE_AMOUNT_MINOR,
            }
        # Retry must reuse the same provider_ref (idempotent).
        self.world.refund_side_effects[provider_ref] = self.world.refund_side_effects[provider_ref]
        self.world.credits.add(provider_ref)
        return {
            "terminal_state": "VERIFIED_RESOLVED",
            "refunded_minor": DUPLICATE_AMOUNT_MINOR,
            "refund_side_effect_count": self.world.refund_side_effects[provider_ref],
            "approval_required": True,
            "unsafe_actions": 0,
            "timeout_recovered": timeout_seen,
            "credit_confirmed": provider_ref in self.world.credits,
            "amount_minor": DUPLICATE_AMOUNT_MINOR,
            "provider_ref": provider_ref,
        }

    def run_refund_pending(self) -> dict[str, object]:
        return {
            "terminal_state": "WAITING_ON_PROVIDER",
            "refunded_minor": 0,
            "refund_side_effect_count": 0,
            "approval_required": False,
            "unsafe_actions": 0,
            "refund_status": "PENDING",
            "credit_confirmed": False,
        }

    def run_browser_to_credit(self) -> dict[str, object]:
        from sentinel_core_assembly.adapters.authority_path import run_browser_to_credit_fixture

        return run_browser_to_credit_fixture(self.world)

    def run_duplicate_approval_deny(self) -> dict[str, object]:
        from sentinel_core_assembly.adapters.authority_path import (
            run_duplicate_approval_deny_fixture,
        )

        return run_duplicate_approval_deny_fixture(self.world)


@dataclass
class MissingPeerBundle:
    """Strict-mode double: one or more required peers absent."""

    missing: tuple[str, ...] = ("verifier.v1",)
    mode: str = "real-peers"
    contract_version: str = CONTRACT_VERSION

    def capabilities_by_port(self) -> dict[str, Capabilities]:
        return {
            port: Capabilities(
                contract_version=self.contract_version,
                component=f"reference-{port}",
                mode=self.mode,  # type: ignore[arg-type]
                port=port,
            )
            for port in REQUIRED_PEERS
            if port not in self.missing
        }

    def run_pending(self) -> dict[str, object]:
        raise PeerFault("PEER_UNAVAILABLE", "Missing peer; journeys must not run")

    def run_merchant_mismatch(self) -> dict[str, object]:
        raise PeerFault("PEER_UNAVAILABLE", "Missing peer; journeys must not run")

    def run_duplicate_payment(self) -> dict[str, object]:
        raise PeerFault("PEER_UNAVAILABLE", "Missing peer; journeys must not run")

    def run_refund_pending(self) -> dict[str, object]:
        raise PeerFault("PEER_UNAVAILABLE", "Missing peer; journeys must not run")

    def run_browser_to_credit(self) -> dict[str, object]:
        raise PeerFault("PEER_UNAVAILABLE", "Missing peer; journeys must not run")

    def run_duplicate_approval_deny(self) -> dict[str, object]:
        raise PeerFault("PEER_UNAVAILABLE", "Missing peer; journeys must not run")


@dataclass
class IncompatiblePeerBundle:
    """Peers present but wrong contract version or fixture mode under strict assembly."""

    contract_version: str = "sentinel.task-contracts.v0"
    mode: str = "fixture"

    def capabilities_by_port(self) -> dict[str, Capabilities]:
        return {
            port: Capabilities(
                contract_version=self.contract_version,
                component=f"bad-{port}",
                mode=self.mode,  # type: ignore[arg-type]
                port=port,
            )
            for port in REQUIRED_PEERS
        }

    def run_pending(self) -> dict[str, object]:
        raise PeerFault("PEER_INCOMPATIBLE", "Incompatible peer")

    def run_merchant_mismatch(self) -> dict[str, object]:
        raise PeerFault("PEER_INCOMPATIBLE", "Incompatible peer")

    def run_duplicate_payment(self) -> dict[str, object]:
        raise PeerFault("PEER_INCOMPATIBLE", "Incompatible peer")

    def run_refund_pending(self) -> dict[str, object]:
        raise PeerFault("PEER_INCOMPATIBLE", "Incompatible peer")

    def run_browser_to_credit(self) -> dict[str, object]:
        raise PeerFault("PEER_INCOMPATIBLE", "Incompatible peer")

    def run_duplicate_approval_deny(self) -> dict[str, object]:
        raise PeerFault("PEER_INCOMPATIBLE", "Incompatible peer")


@dataclass
class HttpPeerBundle:
    """Real-peer adapter: probe HTTP /v1/capabilities; drive journeys over HTTP.

    Never falls back to fixture ReferenceBundle. Provider journeys hit payment-provider
    HTTP (path=provider-sandbox-only). Authority journeys
    (browser_to_credit / duplicate_approval_deny) call case-api → workflow →
    action-ledger (SN-009) → dispatcher-role claim → verifier → closure when
    SENTINEL_V1_AUTHORITY_PATH=1. Labels stay honest; never claim MVP release.
    """

    endpoints: dict[str, str]
    client: object
    tokens: dict[str, str]
    tenant_id: str = "tenant-demo"
    case_id: str = "case-demo-42"
    path: str = "provider-sandbox-only"

    def capabilities_by_port(self) -> dict[str, Capabilities]:
        out: dict[str, Capabilities] = {}
        for port, base in self.endpoints.items():
            if not base:
                continue
            response = self.client.get(f"{base.rstrip('/')}/v1/capabilities")
            if response.status_code >= 500:
                raise PeerFault("PEER_UNAVAILABLE", f"{port} unavailable")
            if response.status_code in (401, 403):
                raise PeerFault("PEER_UNAUTHORIZED", f"{port} unauthorized")
            try:
                body = response.json()
            except Exception as exc:  # noqa: BLE001
                raise PeerFault("PEER_MALFORMED", f"{port} malformed") from exc
            if not isinstance(body, dict):
                raise PeerFault("PEER_MALFORMED", f"{port} malformed")
            out[port] = Capabilities(
                contract_version=str(body.get("contract_version", "")),
                component=str(body.get("component", "")),
                mode=body.get("mode", "fixture"),  # type: ignore[arg-type]
                port=port,
            )
        return out

    def run_pending(self) -> dict[str, object]:
        from sentinel_core_assembly.adapters.sandbox_matrix import journey_seed

        seed = journey_seed("pending")
        order_ref = str(seed["order_reference"])
        payments = self._list_payments(order_ref)
        if not payments:
            raise PeerFault("JOURNEY_SEED_MISSING", f"no payments for {order_ref}")
        if any(str(p.get("status")) != "PENDING" for p in payments):
            raise PeerFault("JOURNEY_PRECONDITION", "expected PENDING payments only")
        return {
            "terminal_state": "WAITING_ON_EVIDENCE",
            "refunded_minor": 0,
            "refund_side_effect_count": 0,
            "approval_required": False,
            "unsafe_actions": 0,
            "case_status": "RECEIVED",
            "payment_status": "PENDING",
            "path": self.path,
        }

    def run_merchant_mismatch(self) -> dict[str, object]:
        from sentinel_core_assembly.adapters.sandbox_matrix import journey_seed

        seed = journey_seed("merchant_mismatch")
        order_ref = str(seed["order_reference"])
        order = self._get_order(order_ref)
        payments = self._list_payments(order_ref)
        if not payments:
            raise PeerFault("JOURNEY_SEED_MISSING", f"no payments for {order_ref}")
        if any(str(p.get("status")) != "CAPTURED" for p in payments):
            raise PeerFault("JOURNEY_PRECONDITION", "expected CAPTURED payments")
        if bool(order.get("paid")):
            raise PeerFault("JOURNEY_PRECONDITION", "merchant order unexpectedly paid")
        return {
            "terminal_state": "NEEDS_HUMAN",
            "refunded_minor": 0,
            "refund_side_effect_count": 0,
            "approval_required": True,
            "unsafe_actions": 0,
            "payment_status": "CAPTURED",
            "order_paid": False,
            "path": self.path,
        }

    def run_duplicate_payment(self) -> dict[str, object]:
        """Hero path against sandbox provider: timeout recover + credit confirm."""
        from sentinel_core_assembly.adapters.sandbox_matrix import journey_seed

        seed = journey_seed("duplicate_payment")
        provider_ref = str(seed["provider_ref"])
        action_id = str(seed["action_id"])
        amount_minor = int(seed["amount_minor"])
        body = {
            "action_id": action_id,
            "provider_ref": provider_ref,
            "transaction_ref": str(seed["transaction_ref"]),
            "amount_minor": amount_minor,
            "currency": "INR",
            "destination": "ORIGINAL_PAYMENT_ROUTE",
        }
        base = self._provider_base()
        admin = self._headers("sandbox-admin")
        dispatcher = self._headers("dispatcher")

        reset = self.client.post(f"{base}/v1/admin/faults/reset", headers=admin)
        self._require_ok(reset, "faults/reset")
        faults = self.client.put(
            f"{base}/v1/admin/faults",
            headers=admin,
            json={"timeout_after_accept": True},
        )
        self._require_ok(faults, "faults")

        try:
            first = self.client.post(
                f"{base}/v1/refunds",
                headers={**dispatcher, "Idempotency-Key": provider_ref},
                json=body,
            )
            # Timeout fault must fire before any admin confirm; 202 means seed is
            # still clean enough to abort without confirming credit.
            if first.status_code != 504:
                raise PeerFault(
                    "JOURNEY_PROVIDER",
                    f"refund create expected 504 after timeout arm, got {first.status_code}",
                )
            timeout_seen = True

            recovered = self.client.get(f"{base}/v1/refunds/{provider_ref}", headers=dispatcher)
            self._require_ok(recovered, "refund lookup")
            recovered_body = recovered.json()
            if str(recovered_body.get("provider_ref")) != provider_ref:
                return {
                    "terminal_state": "FAILED_FINAL",
                    "refunded_minor": 0,
                    "refund_side_effect_count": 2,
                    "approval_required": True,
                    "unsafe_actions": 1,
                    "timeout_recovered": False,
                    "credit_confirmed": False,
                    "amount_minor": amount_minor,
                    "path": self.path,
                }

            # Idempotent retry must keep the same stable provider_ref / single side effect.
            second = self.client.post(
                f"{base}/v1/refunds",
                headers={**dispatcher, "Idempotency-Key": provider_ref},
                json=body,
            )
            if second.status_code not in (504, 202, 409):
                raise PeerFault("JOURNEY_PROVIDER", f"refund retry unexpected {second.status_code}")

            stats = self.client.get(f"{base}/v1/admin/refunds/{provider_ref}/stats", headers=admin)
            self._require_ok(stats, "refund stats")
            side_effects = int(stats.json().get("side_effect_count", -1))
            if side_effects != 1:
                raise PeerFault(
                    "JOURNEY_SIDE_EFFECT",
                    f"expected 1 side effect, got {side_effects}",
                )

            confirm = self.client.post(
                f"{base}/v1/admin/refunds/{provider_ref}/confirm",
                headers=admin,
            )
            self._require_ok(confirm, "refund confirm")
            credit = self.client.post(
                f"{base}/v1/admin/credits/{provider_ref}/confirm",
                headers=admin,
            )
            self._require_ok(credit, "credit confirm")
            credit_get = self.client.get(
                f"{base}/v1/credits/{provider_ref}",
                headers=self._headers("verifier"),
            )
            self._require_ok(credit_get, "credit get")
            credit_confirmed = bool(credit_get.json().get("confirmed"))

            return {
                "terminal_state": "VERIFIED_RESOLVED",
                "refunded_minor": amount_minor,
                "refund_side_effect_count": side_effects,
                "approval_required": True,
                "unsafe_actions": 0,
                "timeout_recovered": timeout_seen,
                "credit_confirmed": credit_confirmed,
                "amount_minor": amount_minor,
                "provider_ref": provider_ref,
                "path": self.path,
            }
        finally:
            self.client.post(f"{base}/v1/admin/faults/reset", headers=admin)

    def run_refund_pending(self) -> dict[str, object]:
        """Read simulator #82 seeded PENDING refund; pending ≠ customer credit."""
        from sentinel_core_assembly.adapters.sandbox_matrix import journey_seed

        seed = journey_seed("refund_pending")
        provider_ref = str(seed["provider_ref"])
        base = self._provider_base()
        dispatcher = self._headers("dispatcher")
        verifier = self._headers("verifier")

        refund_resp = self.client.get(f"{base}/v1/refunds/{provider_ref}", headers=dispatcher)
        if refund_resp.status_code == 404:
            raise PeerFault(
                "JOURNEY_SEED_MISSING",
                f"seeded refund missing: {provider_ref}",
            )
        self._require_ok(refund_resp, "refund get")
        refund = refund_resp.json()
        if str(refund.get("status")) != "PENDING":
            raise PeerFault("JOURNEY_PRECONDITION", "expected PENDING refund")

        credit = self.client.get(f"{base}/v1/credits/{provider_ref}", headers=verifier)
        if credit.status_code != 404:
            raise PeerFault("JOURNEY_PRECONDITION", "pending refund must not imply credit")

        return {
            "terminal_state": "WAITING_ON_PROVIDER",
            "refunded_minor": 0,
            "refund_side_effect_count": 0,
            "approval_required": False,
            "unsafe_actions": 0,
            "refund_status": "PENDING",
            "credit_confirmed": False,
            "path": self.path,
        }

    def run_browser_to_credit(self) -> dict[str, object]:
        from sentinel_core_assembly.adapters.authority_path import run_browser_to_credit_http

        return run_browser_to_credit_http(self)

    def run_duplicate_approval_deny(self) -> dict[str, object]:
        from sentinel_core_assembly.adapters.authority_path import (
            run_duplicate_approval_deny_http,
        )

        return run_duplicate_approval_deny_http(self)

    def _peer_base(self, port: str) -> str:
        base = self.endpoints.get(port, "").rstrip("/")
        if not base:
            raise PeerFault("PEER_MISSING", f"{port} endpoint required")
        return base

    def _provider_base(self) -> str:
        return self._peer_base("payment-provider.v1")

    def _headers(self, role: str) -> dict[str, str]:
        token = self.tokens.get(role, "")
        if not token:
            raise PeerFault("PEER_UNAUTHORIZED", f"missing sandbox token for role={role}")
        return {"Authorization": f"Bearer {token}"}

    def _require_ok(self, response: object, label: str) -> None:
        status = int(getattr(response, "status_code", 0))
        if status >= 400:
            raise PeerFault("JOURNEY_HTTP", f"{label} failed status={status}")

    def _list_payments(self, order_reference: str) -> list[dict[str, object]]:
        response = self.client.get(
            f"{self._provider_base()}/v1/transactions",
            params={"order_reference": order_reference},
            headers=self._headers("workflow"),
        )
        if response.status_code == 404:
            raise PeerFault("JOURNEY_SEED_MISSING", f"order seed missing: {order_reference}")
        self._require_ok(response, "list transactions")
        body = response.json()
        payments = body.get("payments", []) if isinstance(body, dict) else []
        return [p for p in payments if isinstance(p, dict)]

    def _get_order(self, order_reference: str) -> dict[str, object]:
        response = self.client.get(
            f"{self._provider_base()}/v1/orders/{order_reference}",
            headers=self._headers("workflow"),
        )
        if response.status_code == 404:
            raise PeerFault("JOURNEY_SEED_MISSING", f"order seed missing: {order_reference}")
        self._require_ok(response, "get order")
        body = response.json()
        if not isinstance(body, dict):
            raise PeerFault("PEER_MALFORMED", "order body malformed")
        return body
