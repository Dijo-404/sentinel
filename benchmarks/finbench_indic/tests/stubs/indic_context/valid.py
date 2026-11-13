from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ValidIndicContext:
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        text = request.get("input", {}).get("original_text", "synthetic")
        language = request.get("input", {}).get("language", "en-IN")
        return {
            "outcome": "PROPOSAL",
            "reason_codes": ["SYNTHETIC_FIXTURE"],
            "original_text": text,
            "language": language,
            "proposal": {
                "action": "STATUS_UPDATE",
                "message_code": "NEEDS_INPUT",
                "case_id": "case-demo-42",
                "case_revision": 1,
                "evidence_ids": [],
                "policy_version": "policy-fixture-1",
            },
        }
