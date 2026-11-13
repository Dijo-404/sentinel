"""Deterministic EN/TA/HI status templates. Fake generation is always labeled."""

from __future__ import annotations

from sentinel_merchant_comms.domain.types import Case, Language

FAKE_LABEL = "[fake]"

_TEMPLATES: dict[Language, str] = {
    "en": (
        "{label} Status update for case {case_id}: current state is {status}. "
        "Intent {intent}. This text is a deterministic template, not a live model."
    ),
    "ta": (
        "{label} வழக்கு {case_id} நிலை புதுப்பிப்பு: தற்போதைய நிலை {status}. "
        "நோக்கம் {intent}. இது நிர்ணயமான வார்ப்புரு; நேரடி மாதிரி அல்ல."
    ),
    "hi": (
        "{label} मामले {case_id} की स्थिति अद्यतन: वर्तमान स्थिति {status} है। "
        "आशय {intent}. यह निश्चित टेम्पलेट है; लाइव मॉडल नहीं।"
    ),
}


def render_status_body(case: Case, language: Language, *, labeled_fake: bool = True) -> str:
    template = _TEMPLATES[language]
    label = FAKE_LABEL if labeled_fake else ""
    body = template.format(
        label=label,
        case_id=case.case_id,
        status=case.status,
        intent=case.intent,
    )
    return " ".join(body.split())
