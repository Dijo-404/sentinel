"""Scan portal app routes for leftover stub inventory strings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

STUB_PATTERNS: tuple[str, ...] = (
    "Not available yet",
    "Fixture placeholder",
    "not connected to its service yet",
)


class StubHit(TypedDict):
    path: str
    line: int
    text: str


@dataclass(frozen=True)
class StubScanReport:
    status: str
    hits: list[StubHit]


def scan_portal_stubs(web_app_root: Path) -> StubScanReport:
    """Scan ``web_app_root/src/app/**/*.{ts,tsx}`` for stub inventory strings."""
    app_root = web_app_root / "src" / "app"
    hits: list[StubHit] = []
    if app_root.is_dir():
        files = sorted(
            p for p in app_root.rglob("*") if p.is_file() and p.suffix in {".ts", ".tsx"}
        )
        for path in files:
            text = path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                for pattern in STUB_PATTERNS:
                    if pattern in line:
                        hits.append(
                            {
                                "path": str(path),
                                "line": line_no,
                                "text": pattern,
                            }
                        )
    status = "FAIL" if hits else "PASS"
    return StubScanReport(status=status, hits=hits)
