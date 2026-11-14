"""Version/mode/endpoint configuration for core-assembly.v1."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from sentinel_core_assembly.adapters.sandbox_matrix import (
    default_peer_endpoints,
    default_tokens,
    load_sandbox_matrix,
)
from sentinel_core_assembly.domain.types import CONTRACT_SHA256, CONTRACT_VERSION, REQUIRED_PEERS


@dataclass(frozen=True)
class AssemblyConfig:
    mode: str
    contract_version: str
    contract_sha256: str
    peer_endpoints: dict[str, str]
    tokens: dict[str, str] = field(default_factory=dict)
    tenant_id: str = "tenant-demo"
    case_id: str = "case-demo-42"

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> AssemblyConfig:
        env = environ if environ is not None else dict(os.environ)
        matrix = load_sandbox_matrix()
        mapping = {
            "case-api.v1": "CORE_ASSEMBLY_CASE_API_URL",
            "workflow.v1": "CORE_ASSEMBLY_WORKFLOW_URL",
            "action-ledger.v1": "CORE_ASSEMBLY_ACTION_LEDGER_URL",
            "dispatcher.v1": "CORE_ASSEMBLY_DISPATCHER_URL",
            "verifier.v1": "CORE_ASSEMBLY_VERIFIER_URL",
            "payment-provider.v1": "CORE_ASSEMBLY_PAYMENT_PROVIDER_URL",
            "web-shell.v1": "CORE_ASSEMBLY_WEB_SHELL_URL",
        }
        defaults = default_peer_endpoints()
        endpoints = {
            port: (env.get(key, "").strip() or defaults.get(port, ""))
            for port, key in mapping.items()
        }
        # Fixture mode does not require URLs; clear defaults unless explicitly set or real-peers.
        mode = env.get("CORE_ASSEMBLY_MODE", "fixture").strip() or "fixture"
        if mode != "real-peers":
            endpoints = {port: env.get(key, "").strip() for port, key in mapping.items()}

        token_env = {
            "workflow": "CORE_ASSEMBLY_TOKEN_WORKFLOW",
            "dispatcher": "CORE_ASSEMBLY_TOKEN_DISPATCHER",
            "verifier": "CORE_ASSEMBLY_TOKEN_VERIFIER",
            "case-api": "CORE_ASSEMBLY_TOKEN_CASE_API",
            "customer": "CORE_ASSEMBLY_TOKEN_CUSTOMER",
            "supervisor": "CORE_ASSEMBLY_TOKEN_SUPERVISOR",
            "sandbox-admin": "CORE_ASSEMBLY_TOKEN_SANDBOX_ADMIN",
        }
        token_defaults = default_tokens()
        tokens = {
            role: (env.get(key, "").strip() or token_defaults.get(role, ""))
            for role, key in token_env.items()
        }
        return cls(
            mode=mode,
            contract_version=env.get("CORE_ASSEMBLY_CONTRACT_VERSION", CONTRACT_VERSION),
            contract_sha256=env.get("CORE_ASSEMBLY_CONTRACT_SHA256", CONTRACT_SHA256),
            peer_endpoints=endpoints,
            tokens=tokens,
            tenant_id=env.get(
                "CORE_ASSEMBLY_TENANT_ID",
                str(matrix.get("tenant_id", "tenant-demo")),
            ),
            case_id=env.get(
                "CORE_ASSEMBLY_CASE_ID",
                str(matrix.get("case_id", "case-demo-42")),
            ),
        )

    def missing_endpoints(self) -> tuple[str, ...]:
        return tuple(port for port in REQUIRED_PEERS if not self.peer_endpoints.get(port))
