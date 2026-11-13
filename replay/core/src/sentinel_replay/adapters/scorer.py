from __future__ import annotations

from sentinel_replay.domain.models import CandidateOutcome, CheckResult
from sentinel_replay.domain.rules import assert_expected


class DeterministicScorer:
    """Scores observed candidate outcomes against fixture expected postconditions."""

    def score(self, expected: dict, observed: CandidateOutcome) -> tuple[CheckResult, ...]:
        return assert_expected(expected, observed)
