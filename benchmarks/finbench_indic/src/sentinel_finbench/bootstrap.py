"""Composition root: paths, candidates, optional real peers."""

from __future__ import annotations

from pathlib import Path

from sentinel_finbench.adapters.candidates import (
    DeterministicSystemCandidate,
    FakeModelCandidate,
    LiveModelCandidate,
    RecordedBaselineCandidate,
    UnsafeRegressionCandidate,
)
from sentinel_finbench.adapters.real_peer import RealContextPeer, RealRuntimePeer
from sentinel_finbench.application.ports import CandidateRunner
from sentinel_finbench.domain.dataset import DatasetManifest, load_dataset


def package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def datasets_root() -> Path:
    return package_root() / "datasets"


def load_bundled_dataset(dataset_version: str) -> DatasetManifest:
    return load_dataset(datasets_root(), dataset_version)


def select_candidate(name: str, *, live_enabled: bool = False) -> CandidateRunner:
    mapping: dict[str, CandidateRunner] = {
        "recorded": RecordedBaselineCandidate(),
        "fake": FakeModelCandidate(),
        "live": LiveModelCandidate(enabled=live_enabled),
        "system": DeterministicSystemCandidate(),
        "unsafe": UnsafeRegressionCandidate(),
    }
    if name not in mapping:
        raise ValueError(f"unknown candidate {name!r}; choose from {sorted(mapping)}")
    return mapping[name]


def optional_runtime_peer(endpoint: str | None) -> RealRuntimePeer | None:
    if not endpoint:
        return None
    return RealRuntimePeer(endpoint)


def optional_context_peer(endpoint: str | None) -> RealContextPeer | None:
    if not endpoint:
        return None
    return RealContextPeer(endpoint)
