from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel_evaluation.adapters.candidates import (
    CrossTenantCandidate,
    DuplicateEffectCandidate,
    FalseCreditCandidate,
    OverRefundCandidate,
    UnauthorizedActionCandidate,
)
from sentinel_evaluation.application.evaluate import EvaluateError
from sentinel_evaluation.composition.bootstrap import build_service
from sentinel_evaluation.domain.models import CONTRACT_SHA256, CONTRACT_VERSION, SafetyCode

ROOT = Path(__file__).resolve().parents[1]


def _input(run_id: str, mode: str = "fixture", candidate: str = "conforming") -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "run_id": run_id,
        "mode": mode,
        "input_artifacts": [],
        "parameters": {
            "evaluation.candidate": candidate,
            "evaluation.model_mode": "fake",
            "evaluation.contract_sha256": CONTRACT_SHA256,
        },
    }


def test_conforming_candidate_passes_with_disclosures() -> None:
    report = build_service(candidate="conforming").run(_input("acc-conforming"))
    assert report["status"] == "PASS"
    detail = report["detail"]
    assert detail["dataset"]["sha256"]
    assert detail["dataset"]["fixture_count"] == detail["outcomes"]["denominator"]
    assert detail["model_mode"] == "fake"
    assert detail["dataset"]["holdout_count"] >= 1
    assert any(r["holdout_member"] for r in detail["fixture_results"])
    assert detail["splits"]["holdout"]["denominator"] == detail["dataset"]["holdout_count"]
    assert "not product safety certification" in detail["evidence_disclaimer"]


@pytest.mark.parametrize(
    ("candidate", "code"),
    [
        ("unauthorized", SafetyCode.UNAUTHORIZED_ACTION),
        ("over_refund", SafetyCode.OVER_REFUND),
        ("cross_tenant", SafetyCode.CROSS_TENANT),
        ("duplicate_effect", SafetyCode.DUPLICATE_EFFECT),
        ("false_credit", SafetyCode.FALSE_CREDIT),
    ],
)
def test_negative_candidates_trigger_critical_safety(candidate: str, code: SafetyCode) -> None:
    report = build_service(candidate=candidate).run(_input(f"acc-{candidate}", candidate=candidate))
    assert report["status"] == "FAIL"
    assert code.value in report["detail"]["safety"]["critical_failures"]
    safety_check = next(c for c in report["checks"] if c["name"] == "critical_safety")
    assert safety_check["status"] == "FAIL"


def test_critical_safety_overrides_aggregate_quality() -> None:
    # Unauthorized keeps outcome fields matching while violating safety.
    report = build_service(candidate="unauthorized").run(_input("acc-override"))
    detail = report["detail"]
    assert detail["outcomes"]["passed"] == detail["outcomes"]["total"]
    assert detail["safety"]["passed"] is False
    assert detail["safety"]["overrides_quality"] is True
    assert report["status"] == "FAIL"


def test_contract_snapshots_exist() -> None:
    run_input = json.loads((ROOT / "contracts/evaluation.v1.run-input.json").read_text())
    assert run_input["contract_version"] == CONTRACT_VERSION
    example = json.loads(
        (ROOT / "contracts/evaluation.v1.run-report.pass.example.json").read_text()
    )
    assert set(example) >= {
        "contract_version",
        "run_id",
        "mode",
        "status",
        "checks",
        "output_artifacts",
    }


def test_real_peers_rejects_bad_assembly_without_fallback() -> None:
    for stub, code in (
        ("unavailable", "PEER_UNAVAILABLE"),
        ("malformed", "PEER_MALFORMED"),
        ("unauthorized_or_out_of_scope", "PEER_UNAUTHORIZED"),
    ):
        service = build_service(candidate="conforming", mode="real-peers", assembly_stub=stub)
        with pytest.raises(EvaluateError) as exc:
            service.run(_input(f"acc-asm-{stub}", mode="real-peers"))
        assert exc.value.code == code


def test_local_candidate_classes_are_explicit() -> None:
    assert UnauthorizedActionCandidate().candidate_id.startswith("local-unsafe")
    assert OverRefundCandidate().candidate_id.startswith("local-unsafe")
    assert CrossTenantCandidate().candidate_id.startswith("local-unsafe")
    assert DuplicateEffectCandidate().candidate_id.startswith("local-unsafe")
    assert FalseCreditCandidate().candidate_id.startswith("local-unsafe")
