"""CLI exit codes and redacted error surfaces."""

import json
from pathlib import Path

from sentinel_telemetry.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_cli_check_passes(capsys) -> None:
    code = main(["check", "--input", str(ROOT / "fixtures" / "run_input.json")])
    captured = capsys.readouterr()
    assert code == 0
    report = json.loads(captured.out)
    assert report["status"] == "PASS"
    assert report["mode"] == "fixture"


def test_cli_preview_real_peers_unverified(capsys) -> None:
    code = main(["preview", "--input", str(ROOT / "fixtures" / "run_input_real_peers.json")])
    captured = capsys.readouterr()
    assert code == 0
    report = json.loads(captured.out)
    assert report["status"] == "UNVERIFIED"


def test_cli_malformed_input_exits_nonzero(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")
    code = main(["check", "--input", str(bad)])
    captured = capsys.readouterr()
    assert code == 1
    assert "malformed_input_or_io_failure" in captured.err


def test_cli_unsupported_parameter_exits_2(tmp_path: Path, capsys) -> None:
    path = tmp_path / "input.json"
    path.write_text(
        json.dumps(
            {
                "contract_version": "sentinel.task-contracts.v1",
                "run_id": "x",
                "mode": "fixture",
                "input_artifacts": [],
                "parameters": {"not.supported": 1},
            }
        ),
        encoding="utf-8",
    )
    code = main(["check", "--input", str(path)])
    captured = capsys.readouterr()
    assert code == 2
    assert "invalid_or_unsupported_run_input" in captured.err
