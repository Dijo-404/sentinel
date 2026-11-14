"""Canonical V1 sandbox ports/tokens (identity from #84; assembly extras local)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
_TOKENS_PATH = _FIXTURES / "sandbox-tokens.json"
_ASSEMBLY_PATH = _FIXTURES / "sandbox-assembly.json"

# Embedded fallback when fixture files are absent (e.g. editable install layout).
_EMBEDDED_TOKENS: dict[str, Any] = {
    "tenant_id": "tenant-demo",
    "case_id": "case-demo-42",
    "subject_ref": "subject-demo-42",
    "ports": {
        "api": 8080,
        "workflow": 8088,
        "ledger": 8009,
        "dispatcher": 8010,
        "verifier": 8011,
        "identity": 8012,
        "risk": 8013,
        "simulator": 8094,
        "web": 3012,
    },
    "tokens": {
        "tok-workflow": {"principal_id": "svc-workflow", "roles": ["workflow"]},
        "tok-dispatcher": {"principal_id": "svc-dispatcher", "roles": ["dispatcher"]},
        "tok-verifier": {"principal_id": "svc-verifier", "roles": ["verifier"]},
        "tok-case-api": {"principal_id": "svc-case-api", "roles": ["workflow"]},
        "tok-customer": {"principal_id": "customer-demo", "roles": ["customer"]},
        "tok-operator": {"principal_id": "operator-demo", "roles": ["operator"]},
        "tok-supervisor": {"principal_id": "supervisor-demo", "roles": ["supervisor"]},
        "tok-platform-admin": {
            "principal_id": "platform-admin-demo",
            "roles": ["platform_admin"],
        },
        "tok-risk-officer": {
            "principal_id": "risk-officer-demo",
            "roles": ["risk_officer"],
        },
        "tok-sandbox-admin": {
            "principal_id": "svc-sandbox-admin",
            "roles": ["sandbox-admin"],
        },
    },
}

_EMBEDDED_ASSEMBLY: dict[str, Any] = {
    "payment_provider": "simulator",
    "path": "provider-sandbox-only",
    "sn009_authority_exercised": False,
    "base_urls": {
        "case-api.v1": "http://127.0.0.1:8080",
        "workflow.v1": "http://127.0.0.1:8088",
        "action-ledger.v1": "http://127.0.0.1:8009",
        "dispatcher.v1": "http://127.0.0.1:8010",
        "verifier.v1": "http://127.0.0.1:8011",
        "identity.v1": "http://127.0.0.1:8012",
        "risk.v1": "http://127.0.0.1:8013",
        "payment-provider.v1": "http://127.0.0.1:8094",
        "web-shell.v1": "http://127.0.0.1:3012",
    },
    "role_tokens": {
        "workflow": "tok-workflow",
        "dispatcher": "tok-dispatcher",
        "verifier": "tok-verifier",
        "case-api": "tok-case-api",
        "customer": "tok-customer",
        "operator": "tok-operator",
        "supervisor": "tok-supervisor",
        "platform_admin": "tok-platform-admin",
        "risk_officer": "tok-risk-officer",
        "sandbox-admin": "tok-sandbox-admin",
    },
    "journey_seeds": {
        "pending": {
            "order_reference": "JOURNEY-PENDING",
            "expected_payment_status": "PENDING",
        },
        "merchant_mismatch": {
            "order_reference": "JOURNEY-MISMATCH",
            "expected_payment_status": "CAPTURED",
            "expected_order_paid": False,
        },
        "duplicate_payment": {
            "order_reference": "DEMO-ORDER-42",
            "transaction_ref": "TXN-B",
            "action_id": "action-demo-1",
            "provider_ref": "refund-demo-1",
            "amount_minor": 150000,
        },
        "refund_pending": {
            "order_reference": "JOURNEY-REFUND-PENDING",
            "transaction_ref": "TXN-REFUND-PENDING",
            "action_id": "action-refund-pending-1",
            "provider_ref": "refund-pending-1",
            "amount_minor": 150000,
            "seeded": True,
        },
    },
}


def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return dict(fallback)


@lru_cache(maxsize=1)
def load_identity_matrix() -> dict[str, Any]:
    """#84 shape: tok-* → principal objects (+ ports/aliases)."""
    return _read_json(_TOKENS_PATH, _EMBEDDED_TOKENS)


@lru_cache(maxsize=1)
def load_assembly_matrix() -> dict[str, Any]:
    """Assembly-only: role_tokens, base_urls, journey_seeds, path label."""
    return _read_json(_ASSEMBLY_PATH, _EMBEDDED_ASSEMBLY)


@lru_cache(maxsize=1)
def load_sandbox_matrix() -> dict[str, Any]:
    """Merged view for config: identity fields + assembly extras."""
    identity = load_identity_matrix()
    assembly = load_assembly_matrix()
    merged = dict(identity)
    merged.update(
        {
            "payment_provider": assembly.get("payment_provider", "simulator"),
            "path": assembly.get("path", "provider-sandbox-only"),
            "sn009_authority_exercised": bool(assembly.get("sn009_authority_exercised", False)),
            "base_urls": dict(assembly.get("base_urls", {})),
            "role_tokens": dict(assembly.get("role_tokens", {})),
            "journey_seeds": dict(assembly.get("journey_seeds", {})),
        }
    )
    return merged


def default_peer_endpoints() -> dict[str, str]:
    """REQUIRED_PEERS money-path URLs only (identity/risk are optional_rbac)."""
    urls = dict(load_assembly_matrix().get("base_urls", {}))
    return {
        "case-api.v1": str(urls.get("case-api.v1", "")),
        "workflow.v1": str(urls.get("workflow.v1", "")),
        "action-ledger.v1": str(urls.get("action-ledger.v1", "")),
        "dispatcher.v1": str(urls.get("dispatcher.v1", "")),
        "verifier.v1": str(urls.get("verifier.v1", "")),
        "payment-provider.v1": str(urls.get("payment-provider.v1", "")),
        "web-shell.v1": str(urls.get("web-shell.v1", "")),
    }


def optional_rbac_peer_endpoints() -> dict[str, str]:
    """identity.v1 / risk.v1 — optional; not in REQUIRED_PEERS money-path probe."""
    urls = dict(load_assembly_matrix().get("base_urls", {}))
    return {
        "identity.v1": str(urls.get("identity.v1", "")),
        "risk.v1": str(urls.get("risk.v1", "")),
    }


def rbac_path_label() -> str:
    return "rbac-fixture"


def default_tokens() -> dict[str, str]:
    """Role → opaque bearer (from assembly role_tokens; values are #84 tok-* keys)."""
    roles = dict(load_assembly_matrix().get("role_tokens", {}))
    return {str(k): str(v) for k, v in roles.items()}


def journey_seed(name: str) -> dict[str, Any]:
    seeds = dict(load_assembly_matrix().get("journey_seeds", {}))
    if name not in seeds:
        raise KeyError(name)
    return dict(seeds[name])


def payment_provider_label() -> str:
    return str(load_assembly_matrix().get("payment_provider", "simulator"))


def assembly_path_label() -> str:
    return str(load_assembly_matrix().get("path", "provider-sandbox-only"))


def sn009_authority_exercised() -> bool:
    return bool(load_assembly_matrix().get("sn009_authority_exercised", False))
