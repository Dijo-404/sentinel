"""Acceptance: translations/paraphrases stay within one split; hashes disclosed."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from sentinel_finbench.application.evaluate import evaluate_split
from sentinel_finbench.bootstrap import select_candidate
from sentinel_finbench.domain.dataset import (
    DatasetIntegrityError,
    parse_record,
    validate_grouped_splits,
)


def test_bundled_dataset_groups_share_one_split(dataset):
    by_group: dict[str, set[str]] = {}
    for record in dataset.records:
        by_group.setdefault(record.group_id, set()).add(record.split)
        assert record.synthetic
    assert all(len(splits) == 1 for splits in by_group.values())
    # Each group that has a translation/paraphrase keeps it in-split.
    kinds = {}
    for record in dataset.records:
        kinds.setdefault(record.group_id, set()).add(record.variant_kind)
    assert any("translation" in k for k in kinds.values())
    assert any("paraphrase" in k for k in kinds.values())


def test_cross_split_paraphrase_rejected(dataset, tmp_path: Path):
    base = next(r for r in dataset.records if r.variant_kind == "canonical")
    leaked = parse_record(
        {
            "dataset_version": base.dataset_version,
            "scenario_id": f"{base.group_id}_leak",
            "group_id": base.group_id,
            "split": "test" if base.split != "test" else "dev",
            "language": "hi-IN",
            "modality": "text",
            "variant_kind": "paraphrase",
            "input": {"text": "leaked paraphrase"},
            "expected": {
                "intent": base.expected.intent,
                "reported_amount_minor": base.expected.reported_amount_minor,
                "allowed_proposal_types": list(base.expected.allowed_proposal_types),
                "refund_amount_minor": base.expected.refund_amount_minor,
                "required_approval": base.expected.required_approval,
                "final_state": base.expected.final_state,
                "max_financial_effects": base.expected.max_financial_effects,
                "max_unauthorized_effects": base.expected.max_unauthorized_effects,
                "confirmed_total_minor": base.expected.confirmed_total_minor,
            },
            "provenance": {"synthetic": True},
        }
    )
    with pytest.raises(DatasetIntegrityError, match="leak"):
        validate_grouped_splits([*dataset.records, leaked])


def test_baseline_report_discloses_hashes_denominators_variance(dataset):
    report = evaluate_split(dataset, "val", select_candidate("recorded"))
    assert report.dataset_sha256 == dataset.dataset_sha256
    assert report.split_sha256 == dataset.split_sha256["val"]
    assert report.baseline_sha256.startswith("0c728513")
    assert report.model_scores
    assert report.system_scores
    for block in (*report.model_scores, *report.system_scores):
        assert block.denominator >= 0
        assert isinstance(block.variance, float)
        assert block.mean >= 0.0
    payload = report.to_dict()
    assert "dataset_sha256" in payload
    assert "split_sha256" in payload


def test_manifest_hash_mismatch_detected(module_root: Path, tmp_path: Path):
    src = module_root / "datasets" / "indic-fin-v0.1.0"
    dest = tmp_path / "indic-fin-v0.1.0"
    dest.mkdir()
    (dest / "groups").mkdir()
    for path in (src / "groups").glob("*.json"):
        (dest / "groups" / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    bad = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    bad = copy.deepcopy(bad)
    bad["dataset_sha256"] = "0" * 64
    (dest / "manifest.json").write_text(json.dumps(bad), encoding="utf-8")
    from sentinel_finbench.domain.dataset import load_dataset

    with pytest.raises(DatasetIntegrityError, match="hash mismatch"):
        load_dataset(tmp_path, "indic-fin-v0.1.0")
