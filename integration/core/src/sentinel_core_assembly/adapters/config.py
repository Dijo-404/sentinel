"""Version/mode/endpoint configuration for core-assembly.v1."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sentinel_core_assembly.domain.types import CONTRACT_SHA256, CONTRACT_VERSION, REQUIRED_PEERS


@dataclass(frozen=True)
class AssemblyConfig:
    mode: str
    contract_version: str
    contract_sha256: str
    peer_endpoints: dict[str, str]

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> AssemblyConfig:
        env = environ if environ is not None else dict(os.environ)
        mapping = {
            "case-api.v1": "CORE_ASSEMBLY_CASE_API_URL",
            "workflow.v1": "CORE_ASSEMBLY_WORKFLOW_URL",
            "action-ledger.v1": "CORE_ASSEMBLY_ACTION_LEDGER_URL",
            "dispatcher.v1": "CORE_ASSEMBLY_DISPATCHER_URL",
            "verifier.v1": "CORE_ASSEMBLY_VERIFIER_URL",
            "payment-provider.v1": "CORE_ASSEMBLY_PAYMENT_PROVIDER_URL",
            "web-shell.v1": "CORE_ASSEMBLY_WEB_SHELL_URL",
        }
        endpoints = {port: env.get(key, "").strip() for port, key in mapping.items()}
        return cls(
            mode=env.get("CORE_ASSEMBLY_MODE", "fixture").strip() or "fixture",
            contract_version=env.get("CORE_ASSEMBLY_CONTRACT_VERSION", CONTRACT_VERSION),
            contract_sha256=env.get("CORE_ASSEMBLY_CONTRACT_SHA256", CONTRACT_SHA256),
            peer_endpoints=endpoints,
        )

    def missing_endpoints(self) -> tuple[str, ...]:
        return tuple(port for port in REQUIRED_PEERS if not self.peer_endpoints.get(port))
