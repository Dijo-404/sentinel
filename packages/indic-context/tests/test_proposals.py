from __future__ import annotations

from sentinel_indic_context.application.service import IndicContextService
from sentinel_indic_context.domain.types import CONTRACT_SHA256, PORT
from tests.conftest import load_fixture


def test_contract_hash_pinned() -> None:
    assert CONTRACT_SHA256 == "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"
    assert PORT == "indic-context.v1"


def test_tamil_proposal_preserves_provenance(service_factory) -> None:
    service: IndicContextService = service_factory("proposal")
    request, principal = load_fixture("tamil_duplicate.json")
    result, report, normalized = service.propose(request, principal)
    assert result.outcome == "PROPOSAL"
    assert result.original_text == request.input.original_text
    assert result.language == "ta-IN"
    assert result.proposal is not None
    assert result.proposal["action"] == "REQUEST_REFUND"
    assert result.proposal["transaction_ref"] == "TXN-B"
    assert report.evidence_mode == "fake-inference"
    assert report.cost_units == 0.0
    assert report.latency_ms >= 0
    assert normalized.reported_amount_minor == 150000


def test_english_proposal_ok(service_factory) -> None:
    service = service_factory("proposal")
    request, principal = load_fixture("english_refund.json")
    result, report, _ = service.propose(request, principal)
    assert result.outcome == "PROPOSAL"
    assert result.language == "en-IN"
    assert result.original_text == request.input.original_text
    assert report.evidence_mode == "fake-inference"


def test_malformed_proposal_fails(service_factory) -> None:
    service = service_factory("malformed")
    request, principal = load_fixture("english_refund.json")
    result, report, _ = service.propose(request, principal)
    assert result.outcome == "ESCALATE"
    assert result.proposal is None
    assert "MALFORMED_PROPOSAL" in result.reason_codes
    assert report.evidence_mode == "fake-inference"


def test_hallucinated_transaction_ref_fails(service_factory) -> None:
    service = service_factory("hallucinated_ref")
    request, principal = load_fixture("english_refund.json")
    result, _, _ = service.propose(request, principal)
    assert result.outcome == "ESCALATE"
    assert "HALLUCINATED_TRANSACTION_REF" in result.reason_codes


def test_prompt_injection_fails(service_factory) -> None:
    service = service_factory("prompt_injection")
    request, principal = load_fixture("prompt_injection.json")
    result, _, _ = service.propose(request, principal)
    assert result.outcome == "ESCALATE"
    assert "PROMPT_INJECTION" in result.reason_codes
    assert result.original_text == request.input.original_text


def test_unsupported_action_fails(service_factory) -> None:
    service = service_factory("unsupported_action")
    request, principal = load_fixture("english_refund.json")
    result, _, _ = service.propose(request, principal)
    assert result.outcome == "ESCALATE"
    assert "UNSUPPORTED_ACTION" in result.reason_codes
