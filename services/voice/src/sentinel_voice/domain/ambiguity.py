"""Source-preserving ambiguity flags for amount and negation utterances."""

from __future__ import annotations

import re

from sentinel_voice.domain import reason_codes as rc

# Explicit currency/amount cues in Tamil, English, and common Tanglish forms.
_AMOUNT_PATTERNS = (
    re.compile(r"₹\s*\d[\d,]*(?:\.\d+)?"),
    re.compile(r"\b\d[\d,]*(?:\.\d+)?\s*(?:rs|inr|rupees?|ரூபாய்|ரூ)\b", re.IGNORECASE),
    re.compile(r"\b(?:rs|inr|rupees?|ரூபாய்|ரூ)\.?\s*\d[\d,]*(?:\.\d+)?\b", re.IGNORECASE),
    re.compile(r"\b(?:fifteen hundred|thousand five hundred|1500|1,?500)\b", re.IGNORECASE),
)

_NEGATION_PATTERNS = (
    re.compile(r"\b(?:do not|don't|dont|not|never|no)\b", re.IGNORECASE),
    re.compile(r"(?:வேண்டாம்|வேண்டா|இல்ல|illa|illaa|cancel)", re.IGNORECASE),
)

_REFUNDISH = re.compile(
    r"(?:refund|return|chargeback|duplicate|cancel|பணம்|திரும்ப)",
    re.IGNORECASE,
)

_CODE_MIX_HINT = re.compile(
    r"(?:₹|fifteen hundred|thousand five hundred).*(?:illa|ah\?|enna)|"
    r"(?:enna|illa|pannunga).*(?:₹|\d{3,}|fifteen hundred)",
    re.IGNORECASE | re.DOTALL,
)


def analyze_transcript(original_text: str) -> tuple[bool, tuple[str, ...]]:
    """Flag ambiguity; never authorize financial action.

    Always emits NO_FINANCIAL_AUTHORITY. Amount/negation/code-mix cues set
    ambiguous=True so callers clarify instead of acting on speech alone.
    """
    codes: list[str] = []
    amounts = [m.group(0) for pat in _AMOUNT_PATTERNS for m in pat.finditer(original_text)]
    unique_amounts = {a.replace(",", "").lower().replace(" ", "") for a in amounts}
    has_amount = bool(amounts)
    has_negation = any(pat.search(original_text) for pat in _NEGATION_PATTERNS)
    refundish = bool(_REFUNDISH.search(original_text))
    code_mixed = bool(_CODE_MIX_HINT.search(original_text))

    if has_amount and (len(unique_amounts) > 1 or code_mixed):
        codes.append(rc.AMBIGUOUS_AMOUNT)
    elif has_amount and refundish:
        # Amount + refund/complaint language is never actionable from voice alone.
        codes.append(rc.AMBIGUOUS_AMOUNT)

    if has_negation and (has_amount or refundish):
        codes.append(rc.AMBIGUOUS_NEGATION)

    if code_mixed:
        codes.append(rc.CODE_MIXED_AMOUNT)

    codes.append(rc.NO_FINANCIAL_AUTHORITY)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)

    ambiguous = any(
        c in ordered for c in (rc.AMBIGUOUS_AMOUNT, rc.AMBIGUOUS_NEGATION, rc.CODE_MIXED_AMOUNT)
    )
    return ambiguous, tuple(ordered)
