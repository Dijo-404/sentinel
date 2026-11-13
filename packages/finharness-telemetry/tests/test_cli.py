"""CLI check/preview and malformed input exit codes."""

import json
from pathlib import Path

from sentinel_finharness_telemetry.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_cli_preview_fixture(capsys) -> None:
    code = main(["preview", "--input", str(ROOT / "fixtures" / "run_input.json")])
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PASS"
    assert report["mode"] == "fixture"
    assert all(a["evidence_mode"] == "fixture" for a in report["output_artifacts"])


def test_cli_malformed_input_exits_nonzero(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")
    code = main(["check", "--input", str(bad)])
    assert code == 1
    err = json.loads(capsys.readouterr().err)
    assert err["error"] == "malformed_input_or_io_failure"


def test_cli_invalid_contract_exits_2(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "bad-contract.json"
    bad.write_text(
        json.dumps(
            {
                "contract_version": "nope",
                "run_id": "x",
                "mode": "fixture",
                "input_artifacts": [],
                "parameters": {},
            }
        ),
        encoding="utf-8",
    )
    code = main(["check", "--input", str(bad)])
    assert code == 2
    err = json.loads(capsys.readouterr().err)
    assert err["error"] == "invalid_or_unsupported_run_input"
