"""External boundary adapters: candidates and real-peer loaders."""

from .candidates import (
    DeterministicSystemCandidate,
    FakeModelCandidate,
    LiveModelCandidate,
    RecordedBaselineCandidate,
    UnsafeRegressionCandidate,
)
from .real_peer import RealContextPeer, RealRuntimePeer

__all__ = [
    "DeterministicSystemCandidate",
    "FakeModelCandidate",
    "LiveModelCandidate",
    "RealContextPeer",
    "RealRuntimePeer",
    "RecordedBaselineCandidate",
    "UnsafeRegressionCandidate",
]
