"""Evaluate measured driver outcomes against sandbox-validation invariants."""

from __future__ import annotations

from typing import Any

from sentinel_sandbox_pilot.domain.types import (
    DEMO_ACTION_ID,
    DEMO_PROVIDER_REF,
    DEMO_RUNTIME_PIN,
    CheckResult,
)


def evaluate_driver(name: str, outcome: dict[str, Any]) -> CheckResult:
    if name == "second_workflow":
        return _second_workflow(outcome)
    if name == "load":
        return _load(outcome)
    if name == "restart":
        return _restart(outcome)
    if name == "restore":
        return _restore(outcome)
    if name == "kill_switch":
        return _kill_switch(outcome)
    if name == "rollback":
        return _rollback(outcome)
    return CheckResult(f"driver.{name}", "FAIL", "UNKNOWN_DRIVER")


def _ids_preserved(outcome: dict[str, Any]) -> bool:
    return (
        outcome.get("action_id") == DEMO_ACTION_ID
        and outcome.get("provider_ref") == DEMO_PROVIDER_REF
        and outcome.get("minted_second_refund") is False
    )


def _second_workflow(outcome: dict[str, Any]) -> CheckResult:
    if outcome.get("workflow") != "status_update":
        return CheckResult("driver.second_workflow", "FAIL", "SECOND_WORKFLOW_MISSING")
    if outcome.get("refund_side_effect_count", 1) != 0:
        return CheckResult("driver.second_workflow", "FAIL", "UNEXPECTED_REFUND_EFFECT")
    if outcome.get("reused_sdk_ports") is not True:
        return CheckResult("driver.second_workflow", "FAIL", "SDK_PORTS_NOT_REUSED")
    return CheckResult("driver.second_workflow", "PASS", "SECOND_WORKFLOW_OK")


def _load(outcome: dict[str, Any]) -> CheckResult:
    completed = int(outcome.get("completed", 0))
    identity_losses = int(outcome.get("identity_losses", 1))
    if completed < 1:
        return CheckResult("driver.load", "FAIL", "LOAD_NO_WORK")
    if identity_losses != 0:
        return CheckResult("driver.load", "FAIL", "LOAD_IDENTITY_LOSS")
    return CheckResult("driver.load", "PASS", "LOAD_OK")


def _restart(outcome: dict[str, Any]) -> CheckResult:
    if not _ids_preserved(outcome):
        return CheckResult("driver.restart", "FAIL", "IDENTITY_NOT_PRESERVED")
    if outcome.get("reconciled") is not True:
        return CheckResult("driver.restart", "FAIL", "RECONCILIATION_MISSING")
    if outcome.get("status") != "OUTCOME_UNKNOWN":
        return CheckResult("driver.restart", "FAIL", "UNEXPECTED_POST_RESTART_STATUS")
    return CheckResult("driver.restart", "PASS", "RESTART_IDENTITY_OK")


def _restore(outcome: dict[str, Any]) -> CheckResult:
    if outcome.get("restore_ok") is not True:
        return CheckResult("driver.restore", "FAIL", "RESTORE_FAILED")
    if not _ids_preserved(outcome):
        return CheckResult("driver.restore", "FAIL", "IDENTITY_NOT_PRESERVED")
    if outcome.get("runtime_pin") != DEMO_RUNTIME_PIN:
        return CheckResult("driver.restore", "FAIL", "RUNTIME_PIN_LOST")
    return CheckResult("driver.restore", "PASS", "RESTORE_OK")


def _kill_switch(outcome: dict[str, Any]) -> CheckResult:
    if outcome.get("new_writes_blocked") is not True:
        return CheckResult("driver.kill_switch", "FAIL", "NEW_WRITES_NOT_BLOCKED")
    if outcome.get("reconciliation_continued") is not True:
        return CheckResult("driver.kill_switch", "FAIL", "RECONCILIATION_STOPPED")
    if not _ids_preserved(outcome):
        return CheckResult("driver.kill_switch", "FAIL", "IDENTITY_NOT_PRESERVED")
    return CheckResult("driver.kill_switch", "PASS", "KILL_SWITCH_OK")


def _rollback(outcome: dict[str, Any]) -> CheckResult:
    if outcome.get("new_cases_routed_to") != "runtime-b":
        return CheckResult("driver.rollback", "FAIL", "ROUTING_ROLLBACK_MISSING")
    if outcome.get("inflight_runtime_pin") != DEMO_RUNTIME_PIN:
        return CheckResult("driver.rollback", "FAIL", "INFLIGHT_RUNTIME_REPINNED")
    if not _ids_preserved(outcome):
        return CheckResult("driver.rollback", "FAIL", "IDENTITY_NOT_PRESERVED")
    return CheckResult("driver.rollback", "PASS", "ROLLBACK_OK")
