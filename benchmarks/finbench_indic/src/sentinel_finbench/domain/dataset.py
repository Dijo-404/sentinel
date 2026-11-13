"""Grouped synthetic dataset loading, hashing, and split-leakage guards."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

SplitName = Literal["dev", "val", "test"]
ALLOWED_SPLITS: frozenset[str] = frozenset({"dev", "val", "test"})


class DatasetIntegrityError(ValueError):
    """Dataset failed grouped-split or hash integrity checks."""


@dataclass(frozen=True)
class ScenarioExpected:
    intent: str
    reported_amount_minor: int | None
    allowed_proposal_types: tuple[str, ...]
    refund_amount_minor: int | None
    required_approval: bool
    final_state: str
    max_financial_effects: int
    max_unauthorized_effects: int
    confirmed_total_minor: int | None


@dataclass(frozen=True)
class ScenarioRecord:
    dataset_version: str
    scenario_id: str
    group_id: str
    split: SplitName
    language: str
    modality: str
    text: str
    variant_kind: Literal["canonical", "translation", "paraphrase", "fault"]
    expected: ScenarioExpected
    synthetic: bool

    def canonical_bytes(self) -> bytes:
        payload = {
            "dataset_version": self.dataset_version,
            "scenario_id": self.scenario_id,
            "group_id": self.group_id,
            "split": self.split,
            "language": self.language,
            "modality": self.modality,
            "text": self.text,
            "variant_kind": self.variant_kind,
            "expected": {
                "intent": self.expected.intent,
                "reported_amount_minor": self.expected.reported_amount_minor,
                "allowed_proposal_types": list(self.expected.allowed_proposal_types),
                "refund_amount_minor": self.expected.refund_amount_minor,
                "required_approval": self.expected.required_approval,
                "final_state": self.expected.final_state,
                "max_financial_effects": self.expected.max_financial_effects,
                "max_unauthorized_effects": self.expected.max_unauthorized_effects,
                "confirmed_total_minor": self.expected.confirmed_total_minor,
            },
            "synthetic": self.synthetic,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class DatasetManifest:
    dataset_version: str
    records: tuple[ScenarioRecord, ...]
    dataset_sha256: str
    split_sha256: Mapping[str, str]

    def records_for_split(self, split: SplitName) -> tuple[ScenarioRecord, ...]:
        return tuple(r for r in self.records if r.split == split)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_records(records: Sequence[ScenarioRecord]) -> str:
    ordered = sorted(records, key=lambda r: (r.split, r.group_id, r.scenario_id))
    h = hashlib.sha256()
    for record in ordered:
        h.update(record.canonical_bytes())
        h.update(b"\n")
    return h.hexdigest()


def validate_grouped_splits(records: Iterable[ScenarioRecord]) -> None:
    """Translations/paraphrases of one group_id must remain inside one split."""
    group_splits: dict[str, set[str]] = {}
    group_kinds: dict[str, set[str]] = {}
    for record in records:
        if record.split not in ALLOWED_SPLITS:
            raise DatasetIntegrityError(f"unknown split {record.split!r} on {record.scenario_id}")
        if not record.synthetic:
            raise DatasetIntegrityError(f"{record.scenario_id} must be synthetic")
        group_splits.setdefault(record.group_id, set()).add(record.split)
        group_kinds.setdefault(record.group_id, set()).add(record.variant_kind)
    leaked = {gid: splits for gid, splits in group_splits.items() if len(splits) > 1}
    if leaked:
        detail = ", ".join(f"{gid}→{sorted(splits)}" for gid, splits in sorted(leaked.items()))
        raise DatasetIntegrityError(f"translation/paraphrase leak across splits: {detail}")


def _parse_expected(raw: Mapping[str, Any]) -> ScenarioExpected:
    amount = raw.get("reported_amount_minor")
    refund = raw.get("refund_amount_minor")
    confirmed = raw.get("confirmed_total_minor")
    allowed = raw.get("allowed_proposal_types")
    if not isinstance(allowed, list):
        raise DatasetIntegrityError("allowed_proposal_types must be an array")
    return ScenarioExpected(
        intent=str(raw["intent"]),
        reported_amount_minor=None if amount is None else int(amount),
        allowed_proposal_types=tuple(str(x) for x in allowed),
        refund_amount_minor=None if refund is None else int(refund),
        required_approval=bool(raw["required_approval"]),
        final_state=str(raw["final_state"]),
        max_financial_effects=int(raw["max_financial_effects"]),
        max_unauthorized_effects=int(raw["max_unauthorized_effects"]),
        confirmed_total_minor=None if confirmed is None else int(confirmed),
    )


def parse_record(payload: Mapping[str, Any]) -> ScenarioRecord:
    split = payload.get("split")
    if split not in ALLOWED_SPLITS:
        raise DatasetIntegrityError(f"invalid split {split!r}")
    variant = payload.get("variant_kind", "canonical")
    if variant not in {"canonical", "translation", "paraphrase", "fault"}:
        raise DatasetIntegrityError(f"invalid variant_kind {variant!r}")
    input_obj = payload.get("input")
    if not isinstance(input_obj, Mapping):
        raise DatasetIntegrityError("input must be an object")
    provenance = payload.get("provenance") or {}
    if not isinstance(provenance, Mapping):
        raise DatasetIntegrityError("provenance must be an object")
    expected_raw = payload.get("expected")
    if not isinstance(expected_raw, Mapping):
        raise DatasetIntegrityError("expected must be an object")
    return ScenarioRecord(
        dataset_version=str(payload["dataset_version"]),
        scenario_id=str(payload["scenario_id"]),
        group_id=str(payload["group_id"]),
        split=split,  # type: ignore[arg-type]
        language=str(payload["language"]),
        modality=str(payload.get("modality", "text")),
        text=str(input_obj["text"]),
        variant_kind=variant,  # type: ignore[arg-type]
        expected=_parse_expected(expected_raw),
        synthetic=bool(provenance.get("synthetic", False)),
    )


def load_group_file(path: Path) -> list[ScenarioRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, Mapping) and "scenarios" in data:
        items = data["scenarios"]
    elif isinstance(data, list):
        items = data
    else:
        raise DatasetIntegrityError(f"{path} must be a list or {{scenarios: [...]}}")
    if not isinstance(items, list):
        raise DatasetIntegrityError(f"{path} scenarios must be an array")
    return [parse_record(item) for item in items]


def load_dataset(root: Path, dataset_version: str) -> DatasetManifest:
    dataset_dir = root / dataset_version
    groups_dir = dataset_dir / "groups"
    if not groups_dir.is_dir():
        raise DatasetIntegrityError(f"missing groups directory: {groups_dir}")
    records: list[ScenarioRecord] = []
    for path in sorted(groups_dir.glob("*.json")):
        records.extend(load_group_file(path))
    if not records:
        raise DatasetIntegrityError(f"no scenarios under {groups_dir}")
    versions = {r.dataset_version for r in records}
    if versions != {dataset_version}:
        raise DatasetIntegrityError(
            f"record dataset_version mismatch: expected {dataset_version}, got {sorted(versions)}"
        )
    validate_grouped_splits(records)
    split_hashes = {
        split: hash_records([r for r in records if r.split == split])
        for split in sorted({r.split for r in records})
    }
    dataset_hash = hash_records(records)
    manifest_path = dataset_dir / "manifest.json"
    if manifest_path.is_file():
        declared = json.loads(manifest_path.read_text(encoding="utf-8"))
        if declared.get("dataset_version") != dataset_version:
            raise DatasetIntegrityError("manifest dataset_version mismatch")
        if declared.get("dataset_sha256") != dataset_hash:
            raise DatasetIntegrityError(
                "dataset hash mismatch: "
                f"manifest={declared.get('dataset_sha256')} computed={dataset_hash}"
            )
        declared_splits = declared.get("split_sha256") or {}
        for split, digest in split_hashes.items():
            if declared_splits.get(split) != digest:
                raise DatasetIntegrityError(
                    f"split {split} hash mismatch: "
                    f"manifest={declared_splits.get(split)} computed={digest}"
                )
    return DatasetManifest(
        dataset_version=dataset_version,
        records=tuple(records),
        dataset_sha256=dataset_hash,
        split_sha256=split_hashes,
    )
