"""Domain verdict: missing/failed/incompatible/fixture-only block release."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from sentinel_release_mvp.application.verify import load_manifest, verify_manifest
from sentinel_release_mvp.contracts import CONTRACT_SHA256, EvidenceManifest
from sentinel_release_mvp.domain.verdict import evaluate_manifest

MODULE = Path(__file__).resolve().parents[2]
MANIFESTS = MODULE / "contracts" / "manifests"
ARTIFACTS = MODULE / "contracts" / "artifacts"


class VerdictTests(unittest.TestCase):
    def test_positive_real_approves_only_in_strict_mode(self) -> None:
        manifest = load_manifest(MANIFESTS / "positive-real.json")
        strict = evaluate_manifest(
            manifest, require_real_component_evidence=True, artifact_root=ARTIFACTS
        )
        self.assertTrue(strict.release_approved)
        self.assertEqual(strict.status, "PASS")
        soft = evaluate_manifest(manifest, require_real_component_evidence=False)
        self.assertFalse(soft.release_approved)
        self.assertEqual(soft.status, "PASS")
        self.assertIn("SELF_TEST_NOT_RELEASE_PROOF", soft.reason_codes)

    def test_fixture_selftest_never_approves_release(self) -> None:
        manifest = load_manifest(MANIFESTS / "positive-fixture-selftest.json")
        soft = evaluate_manifest(manifest, require_real_component_evidence=False)
        self.assertEqual(soft.status, "PASS")
        self.assertFalse(soft.release_approved)
        strict = evaluate_manifest(manifest, require_real_component_evidence=True)
        self.assertFalse(strict.release_approved)
        self.assertEqual(strict.status, "FAIL")
        self.assertIn("FIXTURE_ONLY_NOT_RELEASE_PROOF", strict.reason_codes)

    def test_missing_component_blocks(self) -> None:
        manifest = load_manifest(MANIFESTS / "negative-missing-component.json")
        verdict = evaluate_manifest(manifest, require_real_component_evidence=True)
        self.assertFalse(verdict.release_approved)
        self.assertIn("MISSING_COMPONENT", verdict.reason_codes)

    def test_failed_check_blocks(self) -> None:
        manifest = load_manifest(MANIFESTS / "negative-failed-check.json")
        verdict = evaluate_manifest(manifest, require_real_component_evidence=True)
        self.assertFalse(verdict.release_approved)
        self.assertIn("FAILED_COMPONENT_CHECK", verdict.reason_codes)

    def test_incompatible_hash_blocks(self) -> None:
        manifest = load_manifest(MANIFESTS / "negative-incompatible-hash.json")
        verdict = evaluate_manifest(manifest, require_real_component_evidence=True)
        self.assertFalse(verdict.release_approved)
        self.assertIn("INCOMPATIBLE_BASELINE", verdict.reason_codes)

    def test_fixture_only_blocks_strict_release(self) -> None:
        manifest = load_manifest(MANIFESTS / "negative-fixture-only.json")
        verdict = evaluate_manifest(manifest, require_real_component_evidence=True)
        self.assertFalse(verdict.release_approved)
        self.assertIn("FIXTURE_ONLY_NOT_RELEASE_PROOF", verdict.reason_codes)

    def test_manifest_carries_versions_hashes_timestamps_and_labels(self) -> None:
        raw = json.loads((MANIFESTS / "positive-real.json").read_text())
        manifest = EvidenceManifest.from_dict(raw)
        self.assertEqual(manifest.baseline_contract_sha256, CONTRACT_SHA256)
        self.assertEqual(manifest.component_under_test, "real")
        self.assertEqual(manifest.payment_provider, "simulator")
        self.assertEqual(manifest.model, "fake")
        self.assertEqual(len(manifest.components), 4)
        for comp in manifest.components:
            self.assertEqual(len(comp.component_commit), 40)
            self.assertEqual(len(comp.artifact_digest), 64)
            self.assertTrue(comp.observed_at.endswith("Z"))
            self.assertTrue(comp.check_command)
            self.assertEqual(comp.check_result, "PASS")

    def test_artifact_digest_mismatch_fails_integrity(self) -> None:
        from sentinel_release_mvp.contracts import ComponentEvidence

        manifest = load_manifest(MANIFESTS / "positive-real.json")
        bad = EvidenceManifest(
            contract_version=manifest.contract_version,
            manifest_id=manifest.manifest_id,
            observed_at=manifest.observed_at,
            baseline_contract_sha256=manifest.baseline_contract_sha256,
            component_under_test=manifest.component_under_test,
            payment_provider=manifest.payment_provider,
            model=manifest.model,
            components=tuple(
                ComponentEvidence.from_dict({**c.to_dict(), "artifact_digest": "0" * 64})
                for c in manifest.components
            ),
            required_checks=manifest.required_checks,
        )
        verdict = evaluate_manifest(
            bad, require_real_component_evidence=True, artifact_root=ARTIFACTS
        )
        self.assertFalse(verdict.release_approved)
        self.assertIn("ARTIFACT_DIGEST_MISMATCH", verdict.reason_codes)

    def test_verify_wire_report_shape(self) -> None:
        manifest = load_manifest(MANIFESTS / "positive-fixture-selftest.json")
        report, verdict = verify_manifest(manifest, mode="fixture", run_id="unit-1")
        self.assertEqual(report.contract_version, "sentinel.task-contracts.v1")
        self.assertEqual(report.mode, "fixture")
        self.assertEqual(report.status, "PASS")
        self.assertFalse(verdict.release_approved)
        self.assertTrue(report.output_artifacts)


if __name__ == "__main__":
    unittest.main()
