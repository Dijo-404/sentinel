"""Load seeded policy artifact catalog from JSON."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_policy.contracts import PolicyInputError
from sentinel_policy.domain.artifacts import PolicyArtifact

MODULE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CATALOG = MODULE_ROOT / "contracts" / "policies.json"

_REQUIRED = frozenset({"policy_id", "version", "status", "updated_at"})


class PolicyCatalog:
    def __init__(self, artifacts: tuple[PolicyArtifact, ...]) -> None:
        self._artifacts = artifacts

    @classmethod
    def from_path(cls, path: Path) -> PolicyCatalog:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "policies" not in raw:
            raise PolicyInputError("INVALID_CONFIG", "policies catalog must have policies array")
        items = raw["policies"]
        if not isinstance(items, list) or not items:
            raise PolicyInputError("INVALID_CONFIG", "policies catalog must be nonempty")
        artifacts: list[PolicyArtifact] = []
        for item in items:
            if not isinstance(item, dict) or set(item) != _REQUIRED:
                raise PolicyInputError(
                    "INVALID_CONFIG",
                    "each policy must have policy_id, version, status, updated_at only",
                )
            for key in _REQUIRED:
                value = item[key]
                if not isinstance(value, str) or not value:
                    raise PolicyInputError("INVALID_CONFIG", f"{key} must be a nonempty string")
            artifacts.append(
                PolicyArtifact(
                    policy_id=item["policy_id"],
                    version=item["version"],
                    status=item["status"],
                    updated_at=item["updated_at"],
                )
            )
        return cls(tuple(artifacts))

    @classmethod
    def default(cls) -> PolicyCatalog:
        return cls.from_path(DEFAULT_CATALOG)

    def list(self) -> tuple[PolicyArtifact, ...]:
        return self._artifacts
