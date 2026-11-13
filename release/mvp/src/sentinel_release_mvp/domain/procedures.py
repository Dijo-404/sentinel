"""Clean-checkout and demo procedure definitions (documentation as data)."""

from __future__ import annotations

from dataclasses import dataclass

from sentinel_release_mvp.contracts import CheckResult


@dataclass(frozen=True)
class ProcedureStep:
    id: str
    title: str
    command: str
    expected: str


CLEAN_CHECKOUT_DEMO: tuple[ProcedureStep, ...] = (
    ProcedureStep(
        id="clone_or_worktree",
        title="Clean checkout or independent worktree",
        command="git fetch origin && git worktree add ../sentinel-release-check origin/main",
        expected="Worktree contains only merged baseline; no sibling task sources required",
    ),
    ProcedureStep(
        id="install_kit",
        title="Install release-evidence kit only",
        command="make -C release/mvp setup",
        expected="uv sync succeeds using release/mvp lockfile alone",
    ),
    ProcedureStep(
        id="self_check",
        title="Run kit self-tests",
        command="make -C release/mvp check",
        expected="Exit 0; report status PASS with release_approved false",
    ),
    ProcedureStep(
        id="negative_manifests",
        title="Confirm negative manifests block release",
        command="sentinel-release-mvp verify --manifest contracts/manifests/negative-fixture-only.json --strict-release",
        expected="Exit nonzero; reason FIXTURE_ONLY_NOT_RELEASE_PROOF",
    ),
    ProcedureStep(
        id="owner_assembly",
        title="Owner-run assembly against real component versions",
        command="sentinel-release-mvp verify --manifest <owner-manifest.json> --strict-release --artifact-root <artifacts>",
        expected="Separate owner decision; kit does not claim product shipped",
    ),
)


def procedure_checklist() -> list[dict[str, str]]:
    return [
        {
            "id": step.id,
            "title": step.title,
            "command": step.command,
            "expected": step.expected,
        }
        for step in CLEAN_CHECKOUT_DEMO
    ]


def validate_procedure_ids(present: set[str]) -> tuple[CheckResult, ...]:
    checks: list[CheckResult] = []
    for step in CLEAN_CHECKOUT_DEMO:
        if step.id in present:
            checks.append(CheckResult(f"procedure:{step.id}", "PASS", "DOCUMENTED"))
        else:
            checks.append(CheckResult(f"procedure:{step.id}", "UNVERIFIED", "NOT_EXECUTED"))
    return tuple(checks)
