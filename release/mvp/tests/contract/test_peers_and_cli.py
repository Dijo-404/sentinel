"""Contract boundary: stubs, real-peer adapter, CLI self-test."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from sentinel_release_mvp.adapters.real_peer import RealPeerRunner
from sentinel_release_mvp.application.verify import render_release_report, verify_manifest, load_manifest
from sentinel_release_mvp.contracts import (
    CONTRACT_VERSION,
    PeerError,
    RunInput,
)
from sentinel_release_mvp.domain.procedures import procedure_checklist
from tests.stubs.core_assembly import valid as ca_valid
from tests.stubs.core_assembly import unavailable as ca_unavail
from tests.stubs.core_assembly import malformed as ca_malformed
from tests.stubs.core_assembly import unauthorized_or_out_of_scope as ca_unauth
from tests.stubs.evaluation import valid as ev_valid
from tests.stubs.replay import valid as rp_valid
from tests.stubs.telemetry import valid as tm_valid

MODULE = Path(__file__).resolve().parents[2]
SRC = MODULE / "src"
PEERS = MODULE / "contracts" / "peers"
MANIFESTS = MODULE / "contracts" / "manifests"
ARTIFACTS = MODULE / "contracts" / "artifacts"


def _run_input(run_id: str = "peer-1") -> RunInput:
    return RunInput(
        contract_version=CONTRACT_VERSION,
        run_id=run_id,
        mode="real-peers",
        input_artifacts=(),
        parameters={},
    )


class StubPeerTests(unittest.TestCase):
    def test_valid_stubs_pass(self) -> None:
        for runner in (ca_valid.RUNNER, ev_valid.RUNNER, rp_valid.RUNNER, tm_valid.RUNNER):
            report = runner.run(_run_input())
            self.assertEqual(report.status, "PASS")
            self.assertEqual(report.contract_version, CONTRACT_VERSION)

    def test_unavailable_raises(self) -> None:
        with self.assertRaises(PeerError) as ctx:
            ca_unavail.RUNNER.run(_run_input())
        self.assertEqual(ctx.exception.code, "PEER_UNAVAILABLE")

    def test_malformed_raises(self) -> None:
        with self.assertRaises(PeerError) as ctx:
            ca_malformed.RUNNER.run(_run_input())
        self.assertEqual(ctx.exception.code, "MALFORMED")

    def test_unauthorized_raises(self) -> None:
        with self.assertRaises(PeerError) as ctx:
            ca_unauth.RUNNER.run(_run_input())
        self.assertEqual(ctx.exception.code, "FORBIDDEN")


class RealPeerAdapterTests(unittest.TestCase):
    def test_file_peer_valid(self) -> None:
        runner = RealPeerRunner(
            "core-assembly.v1", str(PEERS / "core-assembly.valid.json")
        )
        report = runner.run(_run_input())
        self.assertEqual(report.status, "PASS")

    def test_missing_endpoint_unavailable(self) -> None:
        runner = RealPeerRunner("evaluation.v1", "")
        with self.assertRaises(PeerError) as ctx:
            runner.run(_run_input())
        self.assertEqual(ctx.exception.code, "PEER_UNAVAILABLE")

    def test_malformed_file_rejected(self) -> None:
        runner = RealPeerRunner("replay.v1", str(PEERS / "malformed.json"))
        with self.assertRaises(PeerError) as ctx:
            runner.run(_run_input())
        self.assertEqual(ctx.exception.code, "MALFORMED")

    def test_unauthorized_file_rejected(self) -> None:
        runner = RealPeerRunner("telemetry.v1", str(PEERS / "unauthorized.json"))
        with self.assertRaises(PeerError) as ctx:
            runner.run(_run_input())
        self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_no_silent_fixture_fallback_on_peer_failure(self) -> None:
        peers = {
            "core-assembly.v1": RealPeerRunner(
                "core-assembly.v1", str(PEERS / "core-assembly.valid.json")
            ),
            "evaluation.v1": RealPeerRunner("evaluation.v1", ""),
            "replay.v1": RealPeerRunner(
                "replay.v1", str(PEERS / "replay.valid.json")
            ),
            "telemetry.v1": RealPeerRunner(
                "telemetry.v1", str(PEERS / "telemetry.valid.json")
            ),
        }
        manifest = load_manifest(MANIFESTS / "positive-real.json")
        report, verdict = verify_manifest(
            manifest,
            mode="real-peers",
            run_id="peer-fail-1",
            artifact_root=ARTIFACTS,
            peers=peers,
        )
        self.assertEqual(report.status, "FAIL")
        self.assertFalse(verdict.release_approved)
        self.assertTrue(
            any(c.reason_code == "PEER_UNAVAILABLE" for c in report.checks)
        )


class CliAndProcedureTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, PYTHONPATH=str(SRC))
        return subprocess.run(
            [sys.executable, "-m", "sentinel_release_mvp", *args],
            cwd=MODULE,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_self_test_passes_without_release_claim(self) -> None:
        result = self.run_cli("self-test", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertFalse(payload["release_approved"])
        self.assertIn("not claim a product release", payload["note"].lower())

    def test_strict_fixture_only_exits_nonzero(self) -> None:
        result = self.run_cli(
            "verify",
            "--manifest",
            str(MANIFESTS / "negative-fixture-only.json"),
            "--strict-release",
            "--json",
        )
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["verdict"]["release_approved"])

    def test_strict_positive_real_approves_with_artifacts(self) -> None:
        result = self.run_cli(
            "verify",
            "--manifest",
            str(MANIFESTS / "positive-real.json"),
            "--strict-release",
            "--artifact-root",
            str(ARTIFACTS),
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["verdict"]["release_approved"])

    def test_report_rendering(self) -> None:
        result = self.run_cli(
            "report",
            "--manifest",
            str(MANIFESTS / "positive-fixture-selftest.json"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("release_approved: `false`", result.stdout)
        self.assertIn("not product release proof", result.stdout.lower())

    def test_procedure_lists_clean_checkout_steps(self) -> None:
        result = self.run_cli("procedure", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        ids = {s["id"] for s in payload["steps"]}
        self.assertEqual(ids, {s["id"] for s in procedure_checklist()})
        self.assertIn("clone_or_worktree", ids)
        self.assertIn("owner_assembly", ids)

    def test_render_helper_mentions_checks(self) -> None:
        manifest = load_manifest(MANIFESTS / "negative-missing-component.json")
        report, verdict = verify_manifest(
            manifest, mode="real-peers", run_id="render-1"
        )
        text = render_release_report(report, verdict)
        self.assertIn("MISSING_COMPONENT", text)
        self.assertIn("release_approved: `false`", text)

    def test_independence_no_sibling_import(self) -> None:
        # Guard: package imports stay under sentinel_release_mvp / stdlib / tests.
        banned = (
            "sentinel_policy",
            "sentinel_evidence",
            "sentinel_workspace",
            "sentinel_contract_checks",
        )
        for path in (MODULE / "src").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for name in banned:
                self.assertNotIn(f"import {name}", text)
                self.assertNotIn(f"from {name}", text)


if __name__ == "__main__":
    # Allow `tests.stubs` imports when running as script.
    sys.path.insert(0, str(MODULE))
    unittest.main()
