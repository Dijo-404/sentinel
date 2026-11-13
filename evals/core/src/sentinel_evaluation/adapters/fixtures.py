from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sentinel_evaluation.domain.models import EvalFixture, ExpectedOutcome

PACKAGE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET = PACKAGE_ROOT / "fixtures" / "dataset.v1"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_fixture_dict(raw: dict[str, Any]) -> EvalFixture:
    expected_raw = raw["expected"]
    return EvalFixture(
        fixture_id=raw["fixture_id"],
        suite=raw["suite"],
        version=raw["version"],
        split=raw["split"],
        seed=int(raw["seed"]),
        tenant_id=raw["tenant_id"],
        eligible_refund_minor=int(raw["eligible_refund_minor"]),
        currency=raw["currency"],
        credit_actually_confirmed=bool(raw["credit_actually_confirmed"]),
        allowed_actions=tuple(raw["allowed_actions"]),
        expected=ExpectedOutcome(
            terminal_state=expected_raw["terminal_state"],
            refund_side_effect_count=int(expected_raw["refund_side_effect_count"]),
            refunded_minor=int(expected_raw["refunded_minor"]),
            approval_required=bool(expected_raw["approval_required"]),
        ),
        attributes=dict(raw.get("attributes") or {}),
    )


class FileFixtureDataset:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or DEFAULT_DATASET
        manifest_path = self._root / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Missing dataset manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.version = str(manifest["version"])
        fixture_files = [self._root / "cases" / name for name in manifest["fixtures"]]
        loaded: list[EvalFixture] = []
        canonical_cases: list[dict[str, Any]] = []
        for path in fixture_files:
            raw = json.loads(path.read_text(encoding="utf-8"))
            loaded.append(load_fixture_dict(raw))
            canonical_cases.append(json.loads(canonical_json_bytes(raw)))
        envelope = {
            "version": self.version,
            "fixtures": canonical_cases,
        }
        computed = sha256_hex(canonical_json_bytes(envelope))
        expected_hash = manifest.get("sha256")
        if expected_hash and expected_hash != computed:
            raise ValueError(f"Dataset hash mismatch: manifest={expected_hash} computed={computed}")
        self.sha256 = computed
        self._fixtures = loaded

    def fixtures(self) -> list[EvalFixture]:
        return list(self._fixtures)
