"""Framework-free replay domain types and rules."""

from sentinel_replay.domain.models import (
    CandidateOutcome,
    CheckResult,
    FixtureEvent,
    PromotionRecommendation,
    ReplayFixture,
    ReplayModes,
    RunReport,
    SideEffect,
)
from sentinel_replay.domain.rules import assert_expected, decide_promotion, diff_outcomes

__all__ = [
    "CandidateOutcome",
    "CheckResult",
    "FixtureEvent",
    "PromotionRecommendation",
    "ReplayFixture",
    "ReplayModes",
    "RunReport",
    "SideEffect",
    "assert_expected",
    "decide_promotion",
    "diff_outcomes",
]
