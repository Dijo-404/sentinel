"""JSON file case-pin / unknown-action store. Survives process restart."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_finharness_runtime.domain.models import CasePin, UnknownAction


class JsonCaseStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._pins = root / "pins"
        self._unknown = root / "unknown"
        self._pins.mkdir(parents=True, exist_ok=True)
        self._unknown.mkdir(parents=True, exist_ok=True)

    def save_pin(self, pin: CasePin) -> None:
        path = self._pins / f"{pin.case_id}.json"
        path.write_text(pin.model_dump_json(indent=2), encoding="utf-8")

    def get_pin(self, case_id: str) -> CasePin | None:
        path = self._pins / f"{case_id}.json"
        if not path.exists():
            return None
        return CasePin.model_validate_json(path.read_text(encoding="utf-8"))

    def save_unknown(self, action: UnknownAction) -> None:
        path = self._unknown / f"{action.action_id}.json"
        path.write_text(action.model_dump_json(indent=2), encoding="utf-8")

    def get_unknown(self, action_id: str) -> UnknownAction | None:
        path = self._unknown / f"{action_id}.json"
        if not path.exists():
            return None
        return UnknownAction.model_validate_json(path.read_text(encoding="utf-8"))

    def list_unknown(self) -> tuple[UnknownAction, ...]:
        items: list[UnknownAction] = []
        for path in sorted(self._unknown.glob("*.json")):
            items.append(UnknownAction.model_validate_json(path.read_text(encoding="utf-8")))
        return tuple(items)


class MemoryCaseStore:
    """In-process store for unit tests that do not need restart durability."""

    def __init__(self) -> None:
        self._pins: dict[str, CasePin] = {}
        self._unknown: dict[str, UnknownAction] = {}

    def save_pin(self, pin: CasePin) -> None:
        self._pins[pin.case_id] = pin

    def get_pin(self, case_id: str) -> CasePin | None:
        return self._pins.get(case_id)

    def save_unknown(self, action: UnknownAction) -> None:
        self._unknown[action.action_id] = action

    def get_unknown(self, action_id: str) -> UnknownAction | None:
        return self._unknown.get(action_id)

    def list_unknown(self) -> tuple[UnknownAction, ...]:
        return tuple(self._unknown[k] for k in sorted(self._unknown))

    def dump(self) -> dict[str, object]:
        return {
            "pins": {k: v.model_dump() for k, v in self._pins.items()},
            "unknown": {k: v.model_dump() for k, v in self._unknown.items()},
        }

    def load(self, raw: dict[str, object]) -> None:
        pins = raw.get("pins") or {}
        unknown = raw.get("unknown") or {}
        assert isinstance(pins, dict) and isinstance(unknown, dict)
        self._pins = {k: CasePin.model_validate(v) for k, v in pins.items()}
        self._unknown = {k: UnknownAction.model_validate(v) for k, v in unknown.items()}


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
