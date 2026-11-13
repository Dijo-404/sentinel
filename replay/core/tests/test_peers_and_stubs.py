from __future__ import annotations

import pytest
from stubs.evaluation.stub import EvaluationStub
from stubs.evaluation.stub import load_case as load_eval
from stubs.payment_provider.stub import PaymentProviderStub
from stubs.payment_provider.stub import load_case as load_provider

from sentinel_replay.adapters.real_peers import (
    PeerUnavailable,
    RealEvaluationAdapter,
    RealPaymentProviderAdapter,
    RealPeerConfig,
)
from sentinel_replay.application.service import compare_candidates, default_deps


def test_evaluation_stub_cases() -> None:
    assert EvaluationStub("valid").capabilities()["mode"] == "fixture"
    with pytest.raises(RuntimeError):
        EvaluationStub("unavailable").capabilities()
    malformed = EvaluationStub("malformed").capabilities()
    assert malformed["mode"] == "mystery"
    with pytest.raises(PermissionError):
        EvaluationStub("unauthorized_or_out_of_scope").capabilities()
    assert load_eval("valid")["score_response"]["status"] == "PASS"


def test_payment_provider_stub_cases() -> None:
    stub = PaymentProviderStub("valid")
    payments = stub.get_transactions("DEMO-ORDER-42")["payments"]
    assert len(payments) == 2
    refund = stub.create_refund({}, "refund-demo-1")
    assert refund["provider_ref"] == "refund-demo-1"
    with pytest.raises(RuntimeError):
        PaymentProviderStub("unavailable").get_transactions("x")
    bad = PaymentProviderStub("malformed").create_refund({}, "k")
    assert bad["status"] == "MAYBE"
    with pytest.raises(PermissionError):
        PaymentProviderStub("unauthorized_or_out_of_scope").create_refund({}, "k")
    assert load_provider("valid")["capabilities"]["component"] == "payment-provider"


def test_real_adapters_fail_closed_when_absent() -> None:
    with pytest.raises(PeerUnavailable) as eval_exc:
        RealEvaluationAdapter(None).score_suite({})
    assert eval_exc.value.payload["code"] == "PEER_UNAVAILABLE"
    with pytest.raises(PeerUnavailable) as pay_exc:
        RealPaymentProviderAdapter(None).create_refund({}, "k")
    assert pay_exc.value.payload["code"] == "PEER_UNAVAILABLE"


def test_real_peers_mode_without_urls_fails_explicitly() -> None:
    report = compare_candidates(
        run_id="real-peers-missing",
        mode="real-peers",
        deps=default_deps(peer_config=RealPeerConfig()),
    )
    assert report.status == "FAIL"
    assert report.modes.real_evaluation_adapter == "absent"
    assert report.modes.real_payment_provider_adapter == "absent"
    assert any(c.reason_code == "PEER_UNAVAILABLE" for c in report.checks)
    assert all(a.evidence_mode != "real-component" for a in report.output_artifacts)


def test_fixture_run_never_claims_product_evidence() -> None:
    report = compare_candidates(mode="fixture")
    assert report.output_artifacts[0].evidence_mode == "fixture"
    assert report.modes.model_mode == "fake"
