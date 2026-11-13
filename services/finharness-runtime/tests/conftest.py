from __future__ import annotations

import pytest
from stubs import (
    ValidActionLedger,
    ValidEvidence,
    ValidFinHarnessSdk,
    ValidIndicContext,
    ValidPolicy,
    ValidVerifier,
)
from stubs._payloads import REFUND_ACTION

from sentinel_finharness_runtime.adapters.composition import default_manifest, default_shadow_config
from sentinel_finharness_runtime.adapters.safety import ReadOnlyLedger, ShadowSafetyGuard
from sentinel_finharness_runtime.adapters.store import MemoryCaseStore
from sentinel_finharness_runtime.application.runtime import FinHarnessRuntime, RuntimePorts
from sentinel_finharness_runtime.domain.models import CaseManifest, RuntimeConfig


@pytest.fixture
def manifest() -> CaseManifest:
    return default_manifest()


@pytest.fixture
def baseline() -> dict:
    return dict(REFUND_ACTION)


@pytest.fixture
def shadow_config() -> RuntimeConfig:
    return default_shadow_config()


@pytest.fixture
def harness_config(manifest: CaseManifest) -> RuntimeConfig:
    return default_shadow_config(
        execution_mode="harness",
        financial_writes=True,
        runtime_version="finharness-runtime.v2",
    )


def make_runtime(
    config: RuntimeConfig,
    *,
    shadow_ledger: bool = True,
    store: MemoryCaseStore | None = None,
    **peer_overrides,
) -> FinHarnessRuntime:
    defaults = {
        "evidence": ValidEvidence(),
        "policy": ValidPolicy(),
        "ledger_inner": ValidActionLedger(),
        "verifier": ValidVerifier(),
        "indic_context": ValidIndicContext(),
        "sdk": ValidFinHarnessSdk(),
    }
    defaults.update(peer_overrides)
    ledger_inner = defaults.pop("ledger_inner")
    ledger = ReadOnlyLedger(ledger_inner) if shadow_ledger else ledger_inner
    ports = RuntimePorts(
        evidence=defaults["evidence"],
        policy=defaults["policy"],
        ledger=ledger,
        verifier=defaults["verifier"],
        indic_context=defaults["indic_context"],
        sdk=defaults["sdk"],
        store=store or MemoryCaseStore(),
        safety=ShadowSafetyGuard(),
    )
    return FinHarnessRuntime(config=config, ports=ports)
