"""Deterministic routing and comparison rules."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any


def case_in_rollout(case_id: str, rollout_percent: int) -> bool:
    """Stable percent bucket. 0 never routes; 100 always routes when enabled."""
    if rollout_percent <= 0:
        return False
    if rollout_percent >= 100:
        return True
    digest = hashlib.sha256(case_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < rollout_percent


def proposals_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    """Compare actionable proposal fields only."""
    keys = (
        "action",
        "transaction_ref",
        "amount_minor",
        "currency",
        "destination",
        "case_id",
        "case_revision",
    )
    return all(left.get(k) == right.get(k) for k in keys)
