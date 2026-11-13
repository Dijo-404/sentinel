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


@dataclass
class HttpPeerBundle:
    """Real-peer adapter: probe HTTP /v1/capabilities; never fall back to fixtures."""

    endpoints: dict[str, str]
    client: object

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
        raise PeerFault("NOT_WIRED", "Real journey wiring requires owner-selected peers")

    def run_merchant_mismatch(self) -> dict[str, object]:
        raise PeerFault("NOT_WIRED", "Real journey wiring requires owner-selected peers")

    def run_duplicate_payment(self) -> dict[str, object]:
        raise PeerFault("NOT_WIRED", "Real journey wiring requires owner-selected peers")

    def run_refund_pending(self) -> dict[str, object]:
        raise PeerFault("NOT_WIRED", "Real journey wiring requires owner-selected peers")
