"""evaluation.v1: deterministic safety/outcome scoring over versioned fixtures."""

from sentinel_evaluation.application.evaluate import EvaluateService
from sentinel_evaluation.composition.bootstrap import build_fixture_runner
from sentinel_evaluation.domain.models import CONTRACT_SHA256, CONTRACT_VERSION

__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "EvaluateService",
    "build_fixture_runner",
]

__version__ = "0.1.0"
