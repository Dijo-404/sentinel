"""Framework-free evaluation types and scoring rules."""

from sentinel_evaluation.domain.models import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    CandidateObservation,
    EvalFixture,
    ExpectedOutcome,
    FixtureScore,
    SafetyCode,
)
from sentinel_evaluation.domain.scoring import score_fixture, summarize_scores

__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "CandidateObservation",
    "EvalFixture",
    "ExpectedOutcome",
    "FixtureScore",
    "SafetyCode",
    "score_fixture",
    "summarize_scores",
]
