"""FinBench-Indic CLI: recorded/fake evaluation without live peers by default."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from sentinel_finbench.application.evaluate import evaluate_split
from sentinel_finbench.bootstrap import (
    load_bundled_dataset,
    optional_context_peer,
    optional_runtime_peer,
    package_root,
    select_candidate,
)
from sentinel_finbench.contracts import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    ArtifactRef,
    CheckResult,
    PeerError,
    RunReport,
)
from sentinel_finbench.domain.dataset import DatasetIntegrityError, validate_grouped_splits

_MODE_TO_CANDIDATE = {
    "recorded": "recorded",
    "fake-model": "fake",
    "live-model": "live",
    "system": "system",
    "unsafe": "unsafe",
}


def cmd_run(args: argparse.Namespace) -> int:
    try:
        manifest = load_bundled_dataset(args.dataset)
    except DatasetIntegrityError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2

    candidate_name = _MODE_TO_CANDIDATE[args.mode]
    context = optional_context_peer(getattr(args, "context_peer", None))
    runtime = optional_runtime_peer(getattr(args, "runtime_peer", None))
    try:
        candidate = select_candidate(
            candidate_name,
            live_enabled=args.live_model or args.mode == "live-model",
            context=context,
        )
        evidence_mode = "live-provider" if candidate_name == "live" else "fixture"
        report = evaluate_split(manifest, args.split, candidate, evidence_mode=evidence_mode)
    except PeerError as exc:
        print(json.dumps(exc.as_error()), file=sys.stderr)
        return 3

    payload = report.to_dict()
    peers: dict[str, Any] = {}
    if runtime is not None:
        try:
            peers["finharness-runtime.v1"] = dict(
                runtime.run(
                    {
                        "contract_version": CONTRACT_VERSION,
                        "run_id": f"finbench-{report.split}",
                    }
                )
            )
        except PeerError as exc:
            peers["finharness-runtime.v1"] = exc.as_error()
    if context is not None:
        peers["indic-context.v1"] = {"configured": True}
    payload["disclosure"] = {
        "dataset_version": report.dataset_version,
        "dataset_sha256": report.dataset_sha256,
        "split": report.split,
        "split_sha256": report.split_sha256,
        "denominators": {
            s.label: s.denominator for s in (*report.model_scores, *report.system_scores)
        },
        "variance": {s.label: s.variance for s in (*report.model_scores, *report.system_scores)},
        "model_labels": sorted({s.model_label for s in report.model_scores}),
        "system_labels": sorted({s.model_label for s in report.system_scores}),
        "peers": peers,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.overall_status == "PASS" else 1


def cmd_self_test(args: argparse.Namespace) -> int:
    """Fixture-mode acceptance smoke; pytest covers the same invariants."""
    _ = args
    checks: list[CheckResult] = []
    try:
        manifest = load_bundled_dataset("indic-fin-v0.1.0")
        validate_grouped_splits(manifest.records)
        checks.append(CheckResult("grouped_splits", "PASS", "NO_LEAKAGE"))
        baseline = evaluate_split(manifest, "val", select_candidate("recorded"))
        checks.append(
            CheckResult(
                "baseline_val",
                "PASS" if baseline.overall_status == "PASS" else "FAIL",
                "BASELINE_OK" if baseline.overall_status == "PASS" else "BASELINE_FAIL",
            )
        )
        unsafe = evaluate_split(manifest, "val", select_candidate("unsafe"))
        safety_independent = (not unsafe.hard_safety_pass) and unsafe.overall_status == "FAIL"
        avg_present = any(s.denominator > 0 and s.mean > 0 for s in unsafe.model_scores)
        checks.append(
            CheckResult(
                "hard_safety_independent",
                "PASS" if safety_independent and avg_present else "FAIL",
                "SAFETY_GATE_OK" if safety_independent and avg_present else "SAFETY_GATE_FAIL",
            )
        )
        fake = evaluate_split(manifest, "dev", select_candidate("fake"))
        recorded = evaluate_split(manifest, "dev", select_candidate("recorded"))
        distinct = (
            {s.model_label for s in fake.model_scores} == {"fake"}
            and {s.model_label for s in recorded.model_scores} == {"recorded"}
            and all(s.model_label == "system" for s in fake.system_scores)
        )
        checks.append(
            CheckResult(
                "score_channels_distinct",
                "PASS" if distinct else "FAIL",
                "CHANNELS_OK" if distinct else "CHANNELS_MIXED",
            )
        )
    except Exception as exc:  # noqa: BLE001 — surface in report
        checks.append(CheckResult("self_test", "FAIL", type(exc).__name__))
        report = RunReport(
            contract_version=CONTRACT_VERSION,
            run_id="finbench-self-test",
            mode="fixture",
            status="FAIL",
            checks=tuple(checks),
            output_artifacts=(),
        )
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 1

    status = "PASS" if all(c.status == "PASS" for c in checks) else "FAIL"
    artifact = ArtifactRef(
        kind="finbench-evaluation",
        uri=str(package_root() / "fixtures" / "reports" / "self-test.json"),
        sha256=manifest.dataset_sha256,
        component_version="0.1.0",
        evidence_mode="fixture",
    )
    report = RunReport(
        contract_version=CONTRACT_VERSION,
        run_id="finbench-self-test",
        mode="fixture",
        status=status,  # type: ignore[arg-type]
        checks=tuple(checks),
        output_artifacts=(artifact,),
    )
    out = report.to_dict()
    out["port"] = PORT
    out["baseline_sha256"] = CONTRACT_SHA256
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


def cmd_probe_peers(args: argparse.Namespace) -> int:
    """Exercise real-peer adapters. Failures stay visible; no fixture fallback."""
    errors: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    runtime = optional_runtime_peer(args.runtime_peer)
    context = optional_context_peer(args.context_peer)
    if runtime is None and context is None:
        print(
            json.dumps(
                {
                    "code": "PEER_UNAVAILABLE",
                    "message": "configure --runtime-peer and/or --context-peer",
                    "request_id": "request-local-1",
                }
            )
        )
        return 3
    if runtime is not None:
        try:
            results["finharness-runtime.v1"] = dict(
                runtime.run(
                    {
                        "contract_version": CONTRACT_VERSION,
                        "run_id": "probe-runtime",
                        "mode": "real-peers",
                        "input_artifacts": [],
                        "parameters": {},
                    }
                )
            )
        except PeerError as exc:
            errors.append({"peer": exc.peer, **exc.as_error()})
    if context is not None:
        try:
            results["indic-context.v1"] = dict(
                context.propose(
                    {
                        "case": {"contract_version": CONTRACT_VERSION},
                        "input": {"original_text": "synthetic probe", "language": "en-IN"},
                        "evidence": [],
                    }
                )
            )
        except PeerError as exc:
            errors.append({"peer": exc.peer, **exc.as_error()})
    print(json.dumps({"results": results, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentinel-finbench")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Evaluate a split with an injected candidate")
    run.add_argument("--dataset", default="indic-fin-v0.1.0")
    run.add_argument("--split", choices=["dev", "val", "test"], default="val")
    run.add_argument(
        "--mode",
        choices=["recorded", "fake-model", "live-model", "system", "unsafe"],
        default="recorded",
    )
    run.add_argument(
        "--live-model",
        action="store_true",
        help="Explicitly enable live-model candidate (requires --context-peer)",
    )
    run.add_argument(
        "--context-peer",
        default=None,
        help="indic-context.v1 endpoint or file stub (required for live-model)",
    )
    run.add_argument(
        "--runtime-peer",
        default=None,
        help="Optional finharness-runtime.v1 endpoint; disclosed in report peers",
    )
    run.set_defaults(func=cmd_run)

    self_test = sub.add_parser("self-test", help="Fixture self-test / acceptance smoke")
    self_test.set_defaults(func=cmd_self_test)

    probe = sub.add_parser("probe-peers", help="Probe real-peer endpoints (fail closed)")
    probe.add_argument("--runtime-peer", default=None)
    probe.add_argument("--context-peer", default=None)
    probe.set_defaults(func=cmd_probe_peers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
