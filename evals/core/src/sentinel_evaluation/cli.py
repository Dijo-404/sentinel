from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sentinel_evaluation.application.evaluate import EvaluateError
from sentinel_evaluation.composition.bootstrap import build_service
from sentinel_evaluation.domain.models import CONTRACT_SHA256, CONTRACT_VERSION


def _run_input(run_id: str, mode: str, candidate: str) -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "run_id": run_id,
        "mode": mode,
        "input_artifacts": [],
        "parameters": {
            "evaluation.candidate": candidate,
            "evaluation.model_mode": "fake",
            "evaluation.contract_sha256": CONTRACT_SHA256,
        },
    }


def cmd_run(args: argparse.Namespace) -> int:
    service = build_service(
        candidate=args.candidate,
        mode=args.mode,
        assembly_stub=args.assembly_stub,
        candidate_url=args.candidate_url or None,
        assembly_url=getattr(args, "assembly_url", "") or None,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    report = service.run(_run_input(args.run_id, args.mode, args.candidate))
    # Strip in-memory detail for wire RunReport unless --full.
    if args.full:
        wire = report
    else:
        keys = (
            "contract_version",
            "run_id",
            "mode",
            "status",
            "checks",
            "output_artifacts",
        )
        wire = {k: report[k] for k in keys}
    print(json.dumps(wire, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


def cmd_self_test(_args: argparse.Namespace) -> int:
    """Evaluator self-test: conforming PASS; each unsafe FAIL with expected code."""
    from sentinel_evaluation.adapters.candidates import CANDIDATES

    expected_codes = {
        "unauthorized": "UNAUTHORIZED_ACTION",
        "over_refund": "OVER_REFUND",
        "cross_tenant": "CROSS_TENANT",
        "duplicate_effect": "DUPLICATE_EFFECT",
        "false_credit": "FALSE_CREDIT",
    }
    failures: list[str] = []

    conforming = build_service(candidate="conforming", mode="fixture")
    ok = conforming.run(_run_input("self-test-conforming", "fixture", "conforming"))
    if ok["status"] != "PASS":
        failures.append("conforming candidate did not PASS")
    detail = ok["detail"]
    if not detail["dataset"]["sha256"]:
        failures.append("missing dataset hash")
    if detail["model_mode"] != "fake":
        failures.append("model_mode not disclosed as fake")
    if detail["dataset"]["holdout_count"] < 1:
        failures.append("holdout set empty")
    if not any(r["holdout_member"] for r in detail["fixture_results"]):
        failures.append("holdout membership not disclosed on fixture results")

    for name, code in expected_codes.items():
        service = build_service(candidate=name, mode="fixture")
        report = service.run(_run_input(f"self-test-{name}", "fixture", name))
        if report["status"] != "FAIL":
            failures.append(f"{name}: expected FAIL, got {report['status']}")
            continue
        crit = report["detail"]["safety"]["critical_failures"]
        if code not in crit:
            failures.append(f"{name}: expected {code} in {crit}")
        # Unauthorized preserves outcomes → safety overrides quality.
        if name == "unauthorized" and not report["detail"]["safety"]["overrides_quality"]:
            failures.append("unauthorized: expected safety_overrides_quality")

    # Assembly negative stubs must fail closed in real-peers (no fixture fallback).
    for stub, expect_code in (
        ("unavailable", "PEER_UNAVAILABLE"),
        ("malformed", "PEER_MALFORMED"),
        ("unauthorized_or_out_of_scope", "PEER_UNAUTHORIZED"),
    ):
        service = build_service(candidate="conforming", mode="real-peers", assembly_stub=stub)
        try:
            service.run(_run_input(f"self-test-assembly-{stub}", "real-peers", "conforming"))
            failures.append(f"assembly {stub}: expected raise {expect_code}")
        except EvaluateError as exc:
            if exc.code != expect_code:
                failures.append(f"assembly {stub}: expected {expect_code}, got {exc.code}")

    # Valid assembly + conforming candidate in real-peers should PASS self-check.
    valid = build_service(candidate="conforming", mode="real-peers", assembly_stub="valid")
    valid_report = valid.run(_run_input("self-test-assembly-valid", "real-peers", "conforming"))
    if valid_report["status"] != "PASS":
        failures.append("valid assembly real-peers did not PASS")

    known = set(CANDIDATES)
    if known != {"conforming", *expected_codes}:
        failures.append(f"candidate set drift: {known}")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "contract_version": CONTRACT_VERSION,
        "contract_sha256": CONTRACT_SHA256,
        "failures": failures,
        "evidence_disclaimer": (
            "Evaluator self-test is not product safety certification or release evidence."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-evaluation")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run evaluation.v1 against a local or HTTP candidate")
    run.add_argument("--candidate", default="conforming")
    run.add_argument("--mode", choices=("fixture", "real-peers"), default="fixture")
    run.add_argument("--assembly-stub", default="valid")
    run.add_argument("--candidate-url", default="")
    run.add_argument(
        "--assembly-url",
        default="",
        help="core-assembly.v1 base URL when --assembly-stub=live",
    )
    run.add_argument("--run-id", default="eval-local-1")
    run.add_argument("--output-dir", default="")
    run.add_argument("--full", action="store_true")
    run.set_defaults(func=cmd_run)

    self_test = sub.add_parser(
        "self-test",
        help="Standalone evaluator self-test (no product peers)",
    )
    self_test.set_defaults(func=cmd_self_test)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except EvaluateError as exc:
        print(
            json.dumps(
                {"status": "FAIL", "code": exc.code, "message": exc.message},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
