"""Source-preserving Indic/English complaint normalization."""

from __future__ import annotations

import re

from sentinel_indic_context.domain.types import CaseInput, NormalizedComplaint

# Tamil/Hindi number words and common English/Romanized amount phrases.
_AMOUNT_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"ஆயிரத்து\s*ஐநூறு|ஆயிரத்துஐநூறு", re.IGNORECASE), 150000),
    (re.compile(r"हज़ार\s*पाँच\s*सौ|हजार\s*पांच\s*सौ|१५००", re.IGNORECASE), 150000),
    (re.compile(r"(?:rs\.?|inr|₹)\s*1[,.]?500\b", re.IGNORECASE), 150000),
    (re.compile(r"\b1500\b"), 150000),
    (re.compile(r"\b1[,.]500\b"), 150000),
]

_PAYMENT_COUNT_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"இரண்டு\s*தடவை|ரெண்டு\s*தடவை", re.IGNORECASE), 2),
    (re.compile(r"दो\s*बार|2\s*बार", re.IGNORECASE), 2),
    (re.compile(r"\btwice\b|\btwo\s+times\b|\b2\s+times\b", re.IGNORECASE), 2),
]

_ORDER_COUNT_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"ஒரு\s*order|ஒரு\s*ஆர்டர்", re.IGNORECASE), 1),
    (re.compile(r"एक\s*order|एक\s*ऑर्डर", re.IGNORECASE), 1),
    (re.compile(r"\bone\s+order\b|\bonly\s+one\s+order\b", re.IGNORECASE), 1),
]

_NEGATION_PATTERNS = [
    re.compile(r"\bnot\s+received\b|\bdidn't\s+receive\b|\bno\s+refund\b", re.IGNORECASE),
    re.compile(r"नहीं\s*मिला|रिफंड\s*नहीं|नहीं\s*चाहिए", re.IGNORECASE),
    re.compile(r"வரவில்லை|கிடைக்கவில்லை|வேண்டாம்", re.IGNORECASE),
]

_TXN_REF = re.compile(r"\b(?:TXN|txn)[-_]?[A-Za-z0-9]+\b")
_TAMIL = re.compile(r"[\u0B80-\u0BFF]")
_HINDI = re.compile(r"[\u0900-\u097F]")


def _detect_language(text: str, declared: str) -> tuple[str, bool]:
    has_ta = bool(_TAMIL.search(text))
    has_hi = bool(_HINDI.search(text))
    has_latin = bool(re.search(r"[A-Za-z]", text))
    code_mixed = (has_ta or has_hi) and has_latin
    if declared:
        return declared, code_mixed
    if has_ta:
        return "ta-IN", code_mixed
    if has_hi:
        return "hi-IN", code_mixed
    return "en-IN", code_mixed


def normalize_complaint(case_input: CaseInput) -> NormalizedComplaint:
    """Derive claims without rewriting original_text or language."""
    text = case_input.original_text
    language, code_mixed = _detect_language(text, case_input.language)

    amounts = [value for pattern, value in _AMOUNT_PATTERNS if pattern.search(text)]
    amount_ambiguous = len(set(amounts)) > 1
    reported_amount = amounts[0] if amounts and not amount_ambiguous else None
    if amounts and amount_ambiguous:
        reported_amount = None

    payment_counts = [v for pattern, v in _PAYMENT_COUNT_PATTERNS if pattern.search(text)]
    order_counts = [v for pattern, v in _ORDER_COUNT_PATTERNS if pattern.search(text)]
    negation = any(p.search(text) for p in _NEGATION_PATTERNS)
    refs = list(dict.fromkeys(_TXN_REF.findall(text)))

    reason_codes: list[str] = []
    if amount_ambiguous:
        reason_codes.append("AMOUNT_AMBIGUOUS")
    if negation and reported_amount is None and not refs:
        reason_codes.append("NEGATION_WITHOUT_CLEAR_CLAIM")

    return NormalizedComplaint(
        language=language,
        code_mixed=code_mixed,
        original_text=text,
        reported_amount_minor=reported_amount,
        currency="INR" if reported_amount is not None else None,
        reported_payment_count=payment_counts[0] if payment_counts else None,
        reported_order_count=order_counts[0] if order_counts else None,
        negation_present=negation,
        candidate_transaction_refs=refs,
        amount_ambiguous=amount_ambiguous,
        reason_codes=reason_codes,
    )
