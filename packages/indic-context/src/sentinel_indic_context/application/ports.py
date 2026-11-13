"""Narrow ports for Sarvam reasoning adapters."""

from __future__ import annotations

from typing import Protocol

from sentinel_indic_context.domain.types import InferenceReport, ModelRequest, ModelResult


class SarvamPort(Protocol):
    """Structured reasoning adapter. Fake implementations must label themselves."""

    label: str
    evidence_mode: str

    def propose(self, request: ModelRequest) -> tuple[ModelResult, InferenceReport]: ...
