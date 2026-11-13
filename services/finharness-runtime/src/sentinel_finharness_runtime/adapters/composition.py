"""Composition root: wire fixture peers or fail-closed real adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentinel_finharness_runtime.adapters.fixture_peers import (
    FixtureEvidence,
    FixtureIndicContext,
    FixtureLedger,
    FixturePolicy,
    FixtureVerifier,
)
from sentinel_finharness_runtime.adapters.real_peers import (
    RealEvidenceAdapter,
    RealIndicContextAdapter,
    RealLedgerAdapter,
    RealPeerConfig,
    RealPolicyAdapter,
    RealSdkAdapter,
    RealVerifierAdapter,
)
from sentinel_finharness_runtime.adapters.safety import ReadOnlyLedger, ShadowSafetyGuard
from sentinel_finharness_runtime.adapters.sdk_local import LocalSdkFacade
from sentinel_finharness_runtime.adapters.store import JsonCaseStore, MemoryCaseStore
from sentinel_finharness_runtime.application.runtime import FinHarnessRuntime, RuntimePorts
from sentinel_finharness_runtime.domain.models import CaseManifest, RuntimeConfig

_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def default_manifest() -> CaseManifest:
    return CaseManifest.from_mapping(_load_json("case-manifest.json"))


def default_baseline_proposal() -> dict[str, Any]:
    return _load_json("baseline-proposal.json")


def default_shadow_config(**overrides: Any) -> RuntimeConfig:
    raw: dict[str, Any] = {
        "enabled": True,
        "execution_mode": "shadow",
        "runtime_version": "finharness-runtime.v1",
        "financial_writes": False,
        "notifications": False,
        "rollout_percent": 100,
        "allowed_tenants": ["sandbox"],
        "allowed_workflows": ["duplicate_payment"],
        "sandbox_only": True,
    }
    raw.update(overrides)
    return RuntimeConfig.from_mapping(raw)


def fixture_ports(
    *,
    store: MemoryCaseStore | JsonCaseStore | None = None,
    shadow: bool = True,
) -> RuntimePorts:
    evidence = FixtureEvidence()
    policy = FixturePolicy()
    indic = FixtureIndicContext()
    ledger_inner = FixtureLedger()
    ledger: Any = ReadOnlyLedger(ledger_inner) if shadow else ledger_inner
    safety = ShadowSafetyGuard()
    sdk = LocalSdkFacade(indic_context=indic, evidence=evidence, policy=policy)
    return RuntimePorts(
        evidence=evidence,
        policy=policy,
        ledger=ledger,
        verifier=FixtureVerifier(),
        indic_context=indic,
        sdk=sdk,
        store=store or MemoryCaseStore(),
        safety=safety,
    )


def fixture_runtime(
    *,
    state_dir: Path | None = None,
    config: RuntimeConfig | None = None,
) -> tuple[FinHarnessRuntime, CaseManifest, dict[str, Any]]:
    store: MemoryCaseStore | JsonCaseStore
    if state_dir is not None:
        store = JsonCaseStore(state_dir)
    else:
        store = MemoryCaseStore()
    cfg = config or default_shadow_config()
    shadow = cfg.execution_mode == "shadow" or not cfg.financial_writes
    ports = fixture_ports(store=store, shadow=shadow)
    runtime = FinHarnessRuntime(config=cfg, ports=ports)
    return runtime, default_manifest(), default_baseline_proposal()


def real_peer_ports(
    peer_config: RealPeerConfig,
    *,
    store: MemoryCaseStore | JsonCaseStore,
) -> RuntimePorts:
    """Wire real adapters. Absent URLs fail closed on first use — no fixture fallback."""
    evidence = RealEvidenceAdapter(peer_config.evidence_url)
    policy = RealPolicyAdapter(peer_config.policy_url)
    indic = RealIndicContextAdapter(peer_config.indic_context_url)
    ledger = ReadOnlyLedger(RealLedgerAdapter(peer_config.ledger_url))
    return RuntimePorts(
        evidence=evidence,
        policy=policy,
        ledger=ledger,
        verifier=RealVerifierAdapter(peer_config.verifier_url),
        indic_context=indic,
        sdk=RealSdkAdapter(peer_config.sdk_url),
        store=store,
        safety=ShadowSafetyGuard(),
    )
