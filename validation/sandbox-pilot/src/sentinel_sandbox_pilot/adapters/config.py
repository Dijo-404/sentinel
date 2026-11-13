"""Module-local configuration. Never production payment credentials."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from sentinel_sandbox_pilot.domain.types import CONTRACT_SHA256, CONTRACT_VERSION, Mode


@dataclass(frozen=True)
class PilotConfig:
    mode: Mode
    contract_version: str
    contract_sha256: str
    external_authorization: bool = False
    peer_endpoints: dict[str, str] = field(default_factory=dict)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> PilotConfig:
    mode_raw = os.environ.get("SANDBOX_PILOT_MODE", "fixture")
    mode: Mode = "real-peers" if mode_raw == "real-peers" else "fixture"
    endpoints = {
        "core-assembly.v1": os.environ.get("SANDBOX_PILOT_CORE_ASSEMBLY_URL", ""),
        "finharness-runtime.v1": os.environ.get("SANDBOX_PILOT_FINHARNESS_RUNTIME_URL", ""),
        "finbench.v1": os.environ.get("SANDBOX_PILOT_FINBENCH_URL", ""),
        "harness-telemetry.v1": os.environ.get("SANDBOX_PILOT_HARNESS_TELEMETRY_URL", ""),
        "harness-replay.v1": os.environ.get("SANDBOX_PILOT_HARNESS_REPLAY_URL", ""),
    }
    return PilotConfig(
        mode=mode,
        contract_version=os.environ.get("SANDBOX_PILOT_CONTRACT_VERSION", CONTRACT_VERSION),
        contract_sha256=os.environ.get("SANDBOX_PILOT_CONTRACT_SHA256", CONTRACT_SHA256),
        external_authorization=_env_bool("SANDBOX_PILOT_EXTERNAL_AUTHORIZATION", False),
        peer_endpoints={k: v for k, v in endpoints.items() if v},
    )
