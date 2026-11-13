from __future__ import annotations

from pathlib import Path

from conftest import make_runtime

from sentinel_finharness_runtime.adapters.composition import default_shadow_config
from sentinel_finharness_runtime.adapters.store import JsonCaseStore


def test_unknown_action_reconcile_survives_switch_and_restart(tmp_path: Path, manifest):
    state = tmp_path / "state"
    store = JsonCaseStore(state)
    runtime = make_runtime(
        default_shadow_config(execution_mode="harness", financial_writes=True),
        store=store,
        shadow_ledger=False,
    )
    runtime.start_case(case_id="case-demo-42", tenant_id="sandbox", manifest=manifest)
    runtime.record_unknown(
        action_id="action-demo-1",
        case_id="case-demo-42",
        provider_ref="refund-demo-1",
    )

    # Kill switch: stop new writes but keep reconciliation.
    runtime.apply_config(
        default_shadow_config(
            execution_mode="harness",
            financial_writes=False,
            runtime_version="finharness-runtime.v1",
        )
    )
    mid = runtime.reconcile_unknown("action-demo-1")
    assert mid.provider_ref == "refund-demo-1"
    assert mid.minted_new_refund is False
    assert mid.financial_writes_enabled is False
    assert mid.status == "SUBMITTED"

    # Process restart with same durable unknown-action record.
    restarted = make_runtime(
        default_shadow_config(execution_mode="legacy", financial_writes=False, enabled=False),
        store=JsonCaseStore(state),
        shadow_ledger=False,
    )
    after = restarted.reconcile_unknown("action-demo-1")
    assert after.provider_ref == "refund-demo-1"
    assert after.minted_new_refund is False
    assert after.action_id == "action-demo-1"


def test_reconcile_never_mints_new_refund_id(shadow_config, manifest):
    runtime = make_runtime(shadow_config, shadow_ledger=False)
    runtime.start_case(case_id="case-demo-42", tenant_id="sandbox", manifest=manifest)
    runtime.record_unknown(
        action_id="action-demo-1",
        case_id="case-demo-42",
        provider_ref="refund-demo-1",
    )
    result = runtime.reconcile_unknown("action-demo-1")
    assert result.provider_ref == "refund-demo-1"
    assert result.minted_new_refund is False
