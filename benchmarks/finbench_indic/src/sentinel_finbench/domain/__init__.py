"""Framework-free dataset integrity and scoring rules."""

from .dataset import DatasetIntegrityError, ScenarioRecord, load_dataset, validate_grouped_splits
from .scoring import CandidateOutcome, HardSafetyResult, aggregate_scores, score_outcome

__all__ = [
    "CandidateOutcome",
    "DatasetIntegrityError",
    "HardSafetyResult",
    "ScenarioRecord",
    "aggregate_scores",
    "load_dataset",
    "score_outcome",
    "validate_grouped_splits",
]
