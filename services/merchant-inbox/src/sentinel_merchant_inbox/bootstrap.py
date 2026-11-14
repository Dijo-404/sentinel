"""Composition root: config, tokens, peers, store, app."""

from __future__ import annotations

import json
import os
from pathlib import Path

from sentinel_merchant_inbox.adapters.auth import TokenMap
from sentinel_merchant_inbox.adapters.http import create_app
from sentinel_merchant_inbox.adapters.http_peers import HttpCaseApiClient, HttpEvidenceClient
from sentinel_merchant_inbox.adapters.memory_store import MemoryInboxStore
from sentinel_merchant_inbox.adapters.sqlite_store import SqliteInboxStore
from sentinel_merchant_inbox.application.service import MerchantInboxService
from sentinel_merchant_inbox.contracts import parse_exception_item
from sentinel_merchant_inbox.domain.errors import PeerUnavailableError

MODULE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRINCIPALS = MODULE_ROOT / "contracts" / "principals.json"
DEFAULT_FIXTURES = MODULE_ROOT / "contracts" / "exception-items.fixture.json"
DEMO_PEER_TOKEN = "merchant-inbox-peer-demo-token"


def _resolve_mode(mode: str | None) -> str:
    return (
        mode
        or os.environ.get("MERCHANT_INBOX_MODE")
        or os.environ.get("SENTINEL_MODE")
        or "fixture"
    )


def _load_fixture_items(path: Path) -> MemoryInboxStore:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise PeerUnavailableError("fixture items must be a JSON array")
    items = [parse_exception_item(entry) for entry in raw]
    return MemoryInboxStore(items)


def _resolve_peer_token(resolved_mode: str) -> str:
    token = os.environ.get("MERCHANT_INBOX_PEER_TOKEN")
    if resolved_mode == "real-peers":
        if not token or token == DEMO_PEER_TOKEN:
            raise PeerUnavailableError("real-peers requires non-demo MERCHANT_INBOX_PEER_TOKEN")
        return token
    return token or DEMO_PEER_TOKEN


def _resolve_store(
    resolved_mode: str,
    store,
    *,
    fixtures_path: Path | None,
):
    if store is not None:
        return store
    database_url = os.environ.get("MERCHANT_INBOX_DATABASE_URL", "").strip()
    if database_url:
        return SqliteInboxStore.from_url(database_url)
    if resolved_mode == "real-peers":
        raise PeerUnavailableError(
            "real-peers refuses fixture records; inject a store or set MERCHANT_INBOX_DATABASE_URL"
        )
    fixture_path = fixtures_path or Path(
        os.environ.get("MERCHANT_INBOX_FIXTURES_PATH", str(DEFAULT_FIXTURES))
    )
    if not fixture_path.is_absolute():
        fixture_path = (Path.cwd() / fixture_path).resolve()
    return _load_fixture_items(fixture_path)


def build_app(
    *,
    store=None,
    case_api=None,
    evidence=None,
    principals_path: Path | None = None,
    fixtures_path: Path | None = None,
    mode: str | None = None,
):
    resolved_mode = _resolve_mode(mode)
    path = principals_path or Path(
        os.environ.get("MERCHANT_INBOX_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS))
    )
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    tokens = TokenMap.from_path(path)

    resolved_store = _resolve_store(resolved_mode, store, fixtures_path=fixtures_path)

    if case_api is None or evidence is None:
        if resolved_mode != "real-peers":
            raise PeerUnavailableError("Fixture mode requires injected peer ports")
        token = _resolve_peer_token(resolved_mode)
        case_api = case_api or HttpCaseApiClient(os.environ["CASE_API_BASE_URL"], token=token)
        evidence = evidence or HttpEvidenceClient(os.environ["EVIDENCE_BASE_URL"], token=token)

    service = MerchantInboxService(store=resolved_store, case_api=case_api, evidence=evidence)
    return create_app(service=service, tokens=tokens, mode=resolved_mode)


def create_preview_app():
    """Uvicorn factory for local preview; uses in-process valid stubs."""
    from sentinel_merchant_inbox.adapters.local_peers import default_valid_peers

    case_api, evidence = default_valid_peers()
    return build_app(case_api=case_api, evidence=evidence, mode="fixture")
