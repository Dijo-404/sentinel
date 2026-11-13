from __future__ import annotations

from typing import Any, Protocol

from sentinel_evaluation.domain.models import CandidateObservation, EvalFixture


class FixtureDataset(Protocol):
    version: str
    sha256: str

    def fixtures(self) -> list[EvalFixture]: ...


class CandidateRunner(Protocol):
    candidate_id: str
    model_mode: str

    def run(self, fixture: EvalFixture) -> CandidateObservation: ...


class AssemblyPeer(Protocol):
    """core-assembly.v1 probe. Real-peer mode must not silently fall back."""

    def probe(self) -> dict[str, Any]: ...
