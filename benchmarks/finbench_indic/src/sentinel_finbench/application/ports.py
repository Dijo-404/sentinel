"""Injected peer and candidate protocols. No sibling package imports."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from sentinel_finbench.domain.dataset import ScenarioRecord
from sentinel_finbench.domain.scoring import CandidateOutcome


@runtime_checkable
class CandidateRunner(Protocol):
    """Produces per-scenario outcomes. Implementations may be fake/recorded/live-labeled."""

    @property
    def candidate_id(self) -> str: ...

    def run_scenario(self, record: ScenarioRecord) -> CandidateOutcome: ...


@runtime_checkable
class RuntimePeer(Protocol):
    """finharness-runtime.v1 boundary (library/CLI RunReport shape)."""

    def capabilities(self) -> Mapping[str, Any]: ...

    def run(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


@runtime_checkable
class ContextPeer(Protocol):
    """indic-context.v1 boundary: ModelRequest → ModelResult."""

    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...
