"""Wave 4 verify: body asserts fail without seed; pass with seed-shaped JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel_core_assembly.adapters.verify_wave4 import (
    APPROVAL_UI_EXPORT,
    APPROVAL_UI_PACKAGE_NAME,
    SEED_ACTIVITY_ID,
    SEED_ARTICLE_ID,
    SEED_THREAD_ID,
    assert_activity_body,
    assert_approval_ui_package,
    assert_articles_body,
    assert_health_body,
    assert_threads_body,
    assert_voice_capabilities_body,
    verify_wave4,
)


def test_seed_ids_match_peer_modules() -> None:
    assert SEED_THREAD_ID == "thr-seed-tenant-demo"
    assert SEED_ARTICLE_ID == "article-demo-refund-policy"
    assert SEED_ACTIVITY_ID == "act-seed-case-demo-42"


def test_health_assert_requires_ok() -> None:
    with pytest.raises(AssertionError, match="ok"):
        assert_health_body({"status": "degraded"})
    assert_health_body({"status": "ok"})


def test_threads_assert_rejects_empty_and_requires_seed() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_threads_body({"threads": []})
    with pytest.raises(AssertionError, match="thr-seed-tenant-demo"):
        assert_threads_body({"threads": [{"thread_id": "other"}]})
    assert_threads_body({"threads": [{"thread_id": SEED_THREAD_ID, "title": "x"}]})


def test_articles_assert_rejects_empty_and_requires_seed() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_articles_body({"articles": []})
    with pytest.raises(AssertionError, match="article-demo-refund-policy"):
        assert_articles_body({"articles": [{"article_id": "other"}]})
    assert_articles_body({"articles": [{"article_id": SEED_ARTICLE_ID, "title": "x"}]})


def test_activity_assert_rejects_empty_and_requires_seed() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_activity_body({"items": []})
    with pytest.raises(AssertionError, match="act-seed-case-demo-42"):
        assert_activity_body({"items": [{"activity_id": "other"}]})
    assert_activity_body({"items": [{"activity_id": SEED_ACTIVITY_ID, "kind": "case.opened"}]})


def test_voice_capabilities_assert() -> None:
    with pytest.raises(AssertionError, match="component"):
        assert_voice_capabilities_body({"component": "other", "port": "voice.v1"})
    assert_voice_capabilities_body(
        {
            "contract_version": "sentinel.task-contracts.v1",
            "component": "voice",
            "mode": "fixture",
            "port": "voice.v1",
        }
    )


def test_approval_ui_package_smoke_on_repo(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="missing"):
        assert_approval_ui_package(tmp_path)
    pkg = tmp_path / "packages" / "approval-ui"
    pkg.mkdir(parents=True)
    (pkg / "package.json").write_text(
        json.dumps({"name": APPROVAL_UI_PACKAGE_NAME}),
        encoding="utf-8",
    )
    src = pkg / "src"
    src.mkdir()
    (src / "index.ts").write_text(
        f'export {{ {APPROVAL_UI_EXPORT} }} from "./ui/{APPROVAL_UI_EXPORT}.js";\n',
        encoding="utf-8",
    )
    assert_approval_ui_package(tmp_path)


def test_verify_wave4_fails_closed_when_peers_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERIFY_ASSISTANT_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VERIFY_KNOWLEDGE_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VERIFY_OPS_ACTIVITY_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VERIFY_VOICE_URL", "http://127.0.0.1:1")
    report = verify_wave4(dict(__import__("os").environ))
    assert report["status"] == "FAIL"
    assert report.get("reason_code") == "WAVE4_VERIFY_FAILED"
    assert any(not c.get("ok") for c in report["checks"])
