"""Optional indic-context.v1: Sarvam reasoning + Indic source-preserving adapters."""

from sentinel_indic_context.domain.types import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    InferenceReport,
    ModelRequest,
    ModelResult,
)

__version__ = "0.1.0"

__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "PORT",
    "InferenceReport",
    "ModelRequest",
    "ModelResult",
    "__version__",
]
