"""Task-local typed snapshot of module-checks.v1; no sibling imports."""

from dataclasses import dataclass
from typing import Literal

CONTRACT_VERSION = "module-checks.v1"
BASELINE_VERSION = "sentinel.task-contracts.v1"
BASELINE_SHA256 = "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"

Status = Literal["READY", "ABSENT", "UNIMPLEMENTED", "SKIPPED", "PASS", "FAIL",
                 "TIMEOUT", "OUTPUT_LIMIT", "ERROR"]


@dataclass(frozen=True)
class Module:
    id: str
    root: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class ModuleResult:
    id: str
    root: str
    status: Status
    exit_code: int | None = None
    output: str = ""


FAILURES = {"FAIL", "TIMEOUT", "OUTPUT_LIMIT", "ERROR"}
