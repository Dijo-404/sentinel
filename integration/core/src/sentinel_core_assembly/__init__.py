"""core-assembly.v1: journey harness with fixture and strict real-peer modes."""

from .application.assembly import run_assembly
from .domain.types import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    JOURNEYS,
    PORT,
    RunInput,
    RunReport,
)

__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "JOURNEYS",
    "PORT",
    "RunInput",
    "RunReport",
    "run_assembly",
]
