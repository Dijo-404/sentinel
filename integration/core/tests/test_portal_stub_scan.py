"""Portal stub inventory: planted strings FAIL; clean tree PASS."""

from __future__ import annotations

from pathlib import Path

from sentinel_core_assembly.adapters.portal_stub_scan import scan_portal_stubs


def _write_app_page(root: Path, relative: str, body: str) -> Path:
    path = root / "src" / "app" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_scan_fails_when_stub_string_planted(tmp_path: Path) -> None:
    web = tmp_path / "web"
    planted = _write_app_page(
        web,
        "operator/cases/page.tsx",
        "export default function Page() {\n  return <p>Not available yet</p>;\n}\n",
    )
    _write_app_page(web, "ok/page.ts", "export const ok = true;\n")

    report = scan_portal_stubs(web)

    assert report.status == "FAIL"
    assert len(report.hits) == 1
    hit = report.hits[0]
    assert hit["path"] == str(planted)
    assert hit["line"] == 2
    assert hit["text"] == "Not available yet"


def test_scan_finds_all_stub_patterns(tmp_path: Path) -> None:
    web = tmp_path / "web"
    _write_app_page(web, "a/page.tsx", 'const x = "Fixture placeholder";\n')
    _write_app_page(
        web,
        "b/page.ts",
        'const y = "not connected to its service yet";\n',
    )

    report = scan_portal_stubs(web)

    assert report.status == "FAIL"
    texts = {h["text"] for h in report.hits}
    assert texts == {"Fixture placeholder", "not connected to its service yet"}


def test_scan_passes_on_clean_tree(tmp_path: Path) -> None:
    web = tmp_path / "web"
    _write_app_page(
        web,
        "home/page.tsx",
        "export default function Page() {\n  return <p>Ready</p>;\n}\n",
    )
    # Outside src/app — must be ignored even with stub text.
    outside = web / "src" / "components" / "stub.tsx"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text('"Not available yet"\n', encoding="utf-8")

    report = scan_portal_stubs(web)

    assert report.status == "PASS"
    assert report.hits == []


def test_scan_passes_on_current_portal_app() -> None:
    # integration/core → repo root → apps/web
    repo_root = Path(__file__).resolve().parents[3]
    web = repo_root / "apps" / "web"
    assert web.is_dir(), f"expected portal web app at {web}"

    report = scan_portal_stubs(web)

    assert report.status == "PASS", report.hits
    assert report.hits == []
