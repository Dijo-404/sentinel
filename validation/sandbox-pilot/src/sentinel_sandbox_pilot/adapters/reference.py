"""In-process local reference peers for fixture-mode validation drivers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from sentinel_sandbox_pilot.domain.types import (
    CONTRACT_VERSION,
    DEMO_ACTION_ID,
    DEMO_AMOUNT_MINOR,
    DEMO_PROVIDER_REF,
    DEMO_RUNTIME_PIN,
    REQUIRED_PEERS,
    Capabilities,
)


class PeerFault(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class InflightAction:
    action_id: str
    provider_ref: str
    status: str
    runtime_pin: str
    amount_minor: int = DEMO_AMOUNT_MINOR


@dataclass
class PilotWorld:
    """Shared synthetic state for restart/restore/kill-switch/rollback drills."""

    actions: dict[str, InflightAction] = field(default_factory=dict)
    financial_writes_enabled: bool = True
    routing_for_new_cases: str = DEMO_RUNTIME_PIN
    checkpoint: dict[str, Any] | None = None
    write_attempts_after_kill: int = 0
    reconciliations: int = 0

    def seed_inflight(self) -> InflightAction:
        action = InflightAction(
            action_id=DEMO_ACTION_ID,
            provider_ref=DEMO_PROVIDER_REF,
            status="OUTCOME_UNKNOWN",
            runtime_pin=DEMO_RUNTIME_PIN,
        )
        self.actions[action.action_id] = action
        return action

    def snapshot(self) -> dict[str, Any]:
        return {
            "actions": {
                aid: {
                    "action_id": a.action_id,
                    "provider_ref": a.provider_ref,
                    "status": a.status,
                    "runtime_pin": a.runtime_pin,
                    "amount_minor": a.amount_minor,
                }
                for aid, a in self.actions.items()
            },
            "financial_writes_enabled": self.financial_writes_enabled,
            "routing_for_new_cases": self.routing_for_new_cases,
        }

    def restore(self, checkpoint: dict[str, Any]) -> None:
        restored: dict[str, InflightAction] = {}
        for aid, raw in checkpoint.get("actions", {}).items():
            restored[aid] = InflightAction(
                action_id=str(raw["action_id"]),
                provider_ref=str(raw["provider_ref"]),
                status=str(raw["status"]),
                runtime_pin=str(raw["runtime_pin"]),
                amount_minor=int(raw["amount_minor"]),
            )
        self.actions = restored
        self.financial_writes_enabled = bool(checkpoint["financial_writes_enabled"])
        self.routing_for_new_cases = str(checkpoint["routing_for_new_cases"])


@dataclass
class ReferenceBundle:
    """Valid fixture peers implementing ValidationPeers."""

    world: PilotWorld = field(default_factory=PilotWorld)
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

    def run_second_workflow(self) -> dict[str, Any]:
        # Second workflow reuses the same injected peer surface; no refund write.
        return {
            "workflow": "status_update",
            "refund_side_effect_count": 0,
            "reused_sdk_ports": True,
            "peers": list(REQUIRED_PEERS),
        }

    def run_load(self, concurrency: int) -> dict[str, Any]:
        completed = 0
        identity_losses = 0
        for i in range(max(concurrency, 1)):
            action_id = f"action-load-{i}"
            provider_ref = f"refund-load-{i}"
            self.world.actions[action_id] = InflightAction(
                action_id=action_id,
                provider_ref=provider_ref,
                status="PENDING",
                runtime_pin=DEMO_RUNTIME_PIN,
            )
            recovered = self.world.actions[action_id]
            if recovered.action_id != action_id or recovered.provider_ref != provider_ref:
                identity_losses += 1
            completed += 1
        return {
            "completed": completed,
            "identity_losses": identity_losses,
            "concurrency": concurrency,
        }

    def run_restart(self) -> dict[str, Any]:
        action = self.world.seed_inflight()
        # Simulate process death: keep durable identities, drop ephemeral lease only.
        durable = deepcopy(self.world.snapshot())
        self.world.actions.clear()
        self.world.restore(durable)
        recovered = self.world.actions[DEMO_ACTION_ID]
        self.world.reconciliations += 1
        return {
            "action_id": recovered.action_id,
            "provider_ref": recovered.provider_ref,
            "status": recovered.status,
            "reconciled": True,
            "minted_second_refund": recovered.provider_ref != action.provider_ref,
        }

    def run_restore(self, *, fail_restore: bool = False) -> dict[str, Any]:
        self.world.seed_inflight()
        checkpoint = deepcopy(self.world.snapshot())
        self.world.checkpoint = checkpoint
        # Crash / empty memory
        self.world.actions.clear()
        if fail_restore:
            return {
                "restore_ok": False,
                "action_id": "",
                "provider_ref": "",
                "runtime_pin": "",
                "minted_second_refund": False,
            }
        self.world.restore(checkpoint)
        recovered = self.world.actions[DEMO_ACTION_ID]
        return {
            "restore_ok": True,
            "action_id": recovered.action_id,
            "provider_ref": recovered.provider_ref,
            "runtime_pin": recovered.runtime_pin,
            "status": recovered.status,
            "minted_second_refund": False,
        }

    def run_kill_switch(self) -> dict[str, Any]:
        action = self.world.seed_inflight()
        self.world.financial_writes_enabled = False
        if not self.world.financial_writes_enabled:
            self.world.write_attempts_after_kill += 1
            new_writes_blocked = True
        else:
            new_writes_blocked = False
        # Reconciliation of already-submitted action continues under original refs.
        self.world.reconciliations += 1
        recovered = self.world.actions[action.action_id]
        return {
            "action_id": recovered.action_id,
            "provider_ref": recovered.provider_ref,
            "new_writes_blocked": new_writes_blocked,
            "reconciliation_continued": self.world.reconciliations > 0,
            "minted_second_refund": False,
            "status": recovered.status,
        }

    def run_rollback(self) -> dict[str, Any]:
        action = self.world.seed_inflight()
        # Rollback is a routing change for new cases, not a database restore.
        self.world.routing_for_new_cases = "runtime-b"
        recovered = self.world.actions[action.action_id]
        return {
            "action_id": recovered.action_id,
            "provider_ref": recovered.provider_ref,
            "inflight_runtime_pin": recovered.runtime_pin,
            "new_cases_routed_to": self.world.routing_for_new_cases,
            "minted_second_refund": False,
            "status": recovered.status,
        }


@dataclass
class HttpPeerBundle:
    """Strict real-peer probe adapter. Never falls back to fixtures."""

    endpoints: dict[str, str]
    client: Any
    contract_version: str = CONTRACT_VERSION

    def capabilities_by_port(self) -> dict[str, Capabilities]:
        caps: dict[str, Capabilities] = {}
        for port in REQUIRED_PEERS:
            url = self.endpoints.get(port, "").rstrip("/")
            if not url:
                continue
            response = self.client.get(f"{url}/v1/capabilities")
            if response.status_code != 200:
                raise PeerFault("PEER_UNAVAILABLE", f"{port} returned {response.status_code}")
            body = response.json()
            if not isinstance(body, dict):
                raise PeerFault("PEER_MALFORMED", f"{port} capabilities malformed")
            required = {"contract_version", "component", "mode"}
            if not required.issubset(body):
                raise PeerFault("PEER_MALFORMED", f"{port} capabilities incomplete")
            caps[port] = Capabilities(
                contract_version=str(body["contract_version"]),
                component=str(body["component"]),
                mode=body["mode"],
                port=port,
            )
        return caps

    def _deny_fixture_driver(self, name: str) -> dict[str, Any]:
        raise PeerFault(
            "PEER_DRIVER_UNAVAILABLE",
            f"real-peers mode requires live {name} driver; no fixture fallback",
        )

    def run_second_workflow(self) -> dict[str, Any]:
        return self._deny_fixture_driver("second_workflow")

    def run_load(self, concurrency: int) -> dict[str, Any]:
        _ = concurrency
        return self._deny_fixture_driver("load")

    def run_restart(self) -> dict[str, Any]:
        return self._deny_fixture_driver("restart")

    def run_restore(self, *, fail_restore: bool = False) -> dict[str, Any]:
        _ = fail_restore
        return self._deny_fixture_driver("restore")

    def run_kill_switch(self) -> dict[str, Any]:
        return self._deny_fixture_driver("kill_switch")

    def run_rollback(self) -> dict[str, Any]:
        return self._deny_fixture_driver("rollback")
