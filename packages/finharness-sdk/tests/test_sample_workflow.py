from stubs import (
    ValidActionLedger,
    ValidEvidence,
    ValidIndicContext,
    ValidPolicy,
    ValidVerifier,
)

from sentinel_finharness import RuntimeConfig, run_sample_workflow


def test_sample_respects_disabled_defaults(manifest, valid_peers):
    report = run_sample_workflow(
        config=RuntimeConfig(),
        manifest=manifest,
        **valid_peers,
    )
    assert report.routing_enabled is False
    assert report.steps == ("routing-disabled",)
    assert report.baseline_sha256.startswith("0c728513")
    assert report.evidence_mode == "fixture"


def test_sample_shadow_uses_fake_ports_without_writes(manifest, enabled_shadow, valid_peers):
    report = run_sample_workflow(
        config=enabled_shadow,
        manifest=manifest,
        **valid_peers,
    )
    assert report.routing_enabled is True
    assert report.financial_writes is False
    assert "evidence-collected" in report.steps
    assert "model-proposed" in report.steps
    assert "policy-evaluated" in report.steps
    assert "shadow-or-writes-disabled" in report.steps
    assert report.action_id is None
    assert report.policy_outcome == "REQUIRE_APPROVAL"
    assert report.model_outcome == "PROPOSAL"


def test_sample_harness_awaits_approval_before_reserve(manifest, enabled_harness, valid_peers):
    report = run_sample_workflow(
        config=enabled_harness,
        manifest=manifest,
        approval_id=None,
        **valid_peers,
    )
    assert "ledger-proposal" in report.steps
    assert "awaiting-approval" in report.steps
    assert "ledger-reserved" not in report.steps
    assert report.action_id == "action-demo-1"


def test_sample_harness_reserves_only_with_approval(manifest, enabled_harness, valid_peers):
    report = run_sample_workflow(
        config=enabled_harness,
        manifest=manifest,
        approval_id="synthetic-approval_id",
        **valid_peers,
    )
    assert "ledger-reserved" in report.steps
    assert "verifier-assessed" in report.steps
    assert "notification-blocked" in report.steps
    assert report.assessment_status == "WAITING"


def test_sample_notifications_explicit(manifest, valid_peers):
    config = RuntimeConfig.from_mapping(
        {
            "enabled": True,
            "execution_mode": "harness",
            "financial_writes": True,
            "notifications": True,
            "allowed_workflows": [manifest.workflow_name],
            "allowed_tenants": ["sandbox"],
        }
    )
    report = run_sample_workflow(
        config=config,
        manifest=manifest,
        approval_id="synthetic-approval_id",
        evidence=ValidEvidence(),
        policy=ValidPolicy(),
        ledger=ValidActionLedger(),
        verifier=ValidVerifier(),
        indic_context=ValidIndicContext(),
    )
    assert "notification-queued" in report.steps
