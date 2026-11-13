from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_runtime

from sentinel_finharness_runtime.adapters.composition import default_shadow_config
from sentinel_finharness_runtime.adapters.store import JsonCaseStore
from sentinel_finharness_runtime.domain.errors import CapabilityDenied


def test_new_case_pins_current_runtime_version(shadow_config, manifest):
    runtime = make_runtime(shadow_config)
    pin = runtime.start_case(case_id="case-a", tenant_id="sandbox", manifest=manifest)
    assert pin.runtime_version == "finharness-runtime.v1"
    assert pin.execution_mode == "shadow"
    assert runtime.inspect_case("case-a").runtime_version == pin.runtime_version


def test_rollout_switch_and_restart_keep_existing_pin(tmp_path: Path, manifest):
    state = tmp_path / "state"
    store = JsonCaseStore(state)
    cfg_v1 = default_shadow_config(runtime_version="finharness-runtime.v1", rollout_percent=100)
    runtime = make_runtime(cfg_v1, store=store)
    pin = runtime.start_case(case_id="case-pinned", tenant_id="sandbox", manifest=manifest)
    assert pin.runtime_version == "finharness-runtime.v1"

    # Roll forward new cases to v2; existing pin must stay.
    cfg_v2 = default_shadow_config(runtime_version="finharness-runtime.v2", rollout_percent=100)
    runtime.apply_config(cfg_v2)
    assert runtime.inspect_case("case-pinned").runtime_version == "finharness-runtime.v1"

    # Simulate process restart with durable store + rolled-back percent.
    restarted = make_runtime(
        default_shadow_config(runtime_version="finharness-runtime.v2", rollout_percent=0),
        store=JsonCaseStore(state),
    )
    assert restarted.inspect_case("case-pinned").runtime_version == "finharness-runtime.v1"

    with pytest.raises(CapabilityDenied, match="rollout"):
        restarted.start_case(
            case_id="case-new-after-rollback",
            tenant_id="sandbox",
            manifest=manifest,
        )


def test_rollback_allows_new_cases_after_reroll(tmp_path: Path, manifest):
    state = tmp_path / "state"
    store = JsonCaseStore(state)
    runtime = make_runtime(
        default_shadow_config(runtime_version="finharness-runtime.v1"),
        store=store,
    )
    runtime.start_case(case_id="case-old", tenant_id="sandbox", manifest=manifest)

    runtime.apply_config(
        default_shadow_config(runtime_version="finharness-runtime.v2", rollout_percent=0)
    )
    with pytest.raises(CapabilityDenied):
        runtime.start_case(case_id="case-blocked", tenant_id="sandbox", manifest=manifest)

    runtime.apply_config(
        default_shadow_config(runtime_version="finharness-runtime.v2", rollout_percent=100)
    )
    new_pin = runtime.start_case(case_id="case-new", tenant_id="sandbox", manifest=manifest)
    assert new_pin.runtime_version == "finharness-runtime.v2"
    assert runtime.inspect_case("case-old").runtime_version == "finharness-runtime.v1"


def test_sandbox_harness_routing_guarded(harness_config, manifest):
    runtime = make_runtime(harness_config, shadow_ledger=False)
    runtime.start_case(case_id="case-sandbox", tenant_id="sandbox", manifest=manifest)
    decision = runtime.route_sandbox("case-sandbox")
    assert decision.routed is True
    assert decision.financial_writes is True
    assert decision.reason_code == "SANDBOX_HARNESS_ROUTED"
    assert runtime.inspect_case("case-sandbox").runtime_version == "finharness-runtime.v2"

    runtime.apply_config(
        default_shadow_config(
            execution_mode="harness",
            financial_writes=False,
            runtime_version="finharness-runtime.v9",
        )
    )
    # Pin retains start-time version; kill switch disables writes on route decision.
    assert runtime.inspect_case("case-sandbox").runtime_version == "finharness-runtime.v2"
    decision2 = runtime.route_sandbox("case-sandbox")
    assert decision2.runtime_version == "finharness-runtime.v2"
    assert decision2.financial_writes is False
    assert decision2.reason_code == "SANDBOX_HARNESS_READ_ONLY"
