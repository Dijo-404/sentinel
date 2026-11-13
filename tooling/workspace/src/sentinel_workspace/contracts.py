"""Task-local typed snapshot of module-checks.v1; no sibling imports."""

from dataclasses import dataclass
from typing import Literal

CONTRACT_VERSION = "module-checks.v1"
BASELINE_VERSION = "sentinel.task-contracts.v1"
BASELINE_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"

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
