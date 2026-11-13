from __future__ import annotations

from sentinel_indic_context.domain.normalize import normalize_complaint
from tests.conftest import load_fixture


def test_tamil_fixture_preserves_original_text_and_language() -> None:
    request, _ = load_fixture("tamil_duplicate.json")
    normalized = normalize_complaint(request.input)
    assert normalized.original_text == request.input.original_text
    assert normalized.language == "ta-IN"
    assert normalized.code_mixed is True
    assert normalized.reported_amount_minor == 150000
    assert normalized.reported_payment_count == 2
    assert normalized.reported_order_count == 1
    assert normalized.currency == "INR"


def test_hindi_negation_fixture_preserves_text() -> None:
    request, _ = load_fixture("hindi_negation.json")
    normalized = normalize_complaint(request.input)
    assert normalized.original_text == request.input.original_text
    assert normalized.language == "hi-IN"
    assert normalized.negation_present is True


def test_english_amount_count_and_reference() -> None:
    request, _ = load_fixture("english_refund.json")
    normalized = normalize_complaint(request.input)
    assert normalized.original_text == request.input.original_text
    assert normalized.language == "en-IN"
    assert normalized.reported_amount_minor == 150000
    assert normalized.reported_payment_count == 2
    assert normalized.reported_order_count == 1
    assert "TXN-B" in normalized.candidate_transaction_refs
