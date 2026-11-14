"""Runtime dependencies injected into graph nodes via LangGraph config."""

from __future__ import annotations

from dataclasses import dataclass

from sentinel_workflow.application.ports import (
    CaseApiPort,
    EvidencePort,
    LedgerPort,
    ModelPort,
    OutboxPort,
    PolicyPort,
    RiskPort,
    VerifierPort,
)


@dataclass(frozen=True)
class GraphDeps:
    case_api: CaseApiPort
    evidence: EvidencePort
    policy: PolicyPort
    ledger: LedgerPort
    verifier: VerifierPort
    model: ModelPort
    outbox: OutboxPort
    risk: RiskPort
    policy_version: str = "demo-policy-v1"


CONFIG_KEY = "sentinel_workflow_deps"


def deps_from_config(config: dict | None) -> GraphDeps:
    configurable = (config or {}).get("configurable") or {}
    deps = configurable.get(CONFIG_KEY)
    if deps is None:
        raise RuntimeError("Workflow graph dependencies were not configured")
    return deps
