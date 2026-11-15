"""Composition root: config, tokens, clock, app."""

from __future__ import annotations

import os
from pathlib import Path

from sentinel_policy.adapters.auth import TokenMap
from sentinel_policy.adapters.catalog import PolicyCatalog
from sentinel_policy.adapters.clock import SystemClock
from sentinel_policy.adapters.http import create_app
from sentinel_policy.application.evaluate import EvaluatePolicy
from sentinel_policy.application.list_policies import ListPolicies

MODULE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRINCIPALS = MODULE_ROOT / "contracts" / "principals.json"
DEFAULT_POLICIES = MODULE_ROOT / "contracts" / "policies.json"


def build_app(
    *,
    principals_path: Path | None = None,
    policies_path: Path | None = None,
    mode: str | None = None,
):
    path = principals_path or Path(
        os.environ.get("POLICY_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS))
    )
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    catalog_path = policies_path or Path(
        os.environ.get("POLICY_CATALOG_PATH", str(DEFAULT_POLICIES))
    )
    if not catalog_path.is_absolute():
        catalog_path = (Path.cwd() / catalog_path).resolve()
    tokens = TokenMap.from_path(path)
    evaluate = EvaluatePolicy(SystemClock())
    list_policies = ListPolicies(PolicyCatalog.from_path(catalog_path))
    return create_app(
        evaluate=evaluate,
        tokens=tokens,
        list_policies=list_policies,
        mode=mode or os.environ.get("POLICY_MODE", "fixture"),
    )
