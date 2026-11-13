"""CLI smoke: self-test and recorded run disclose evaluation payload."""

from __future__ import annotations

import json

from sentinel_finbench.cli import main


def test_self_test_passes(capsys):
    code = main(["self-test"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["status"] == "PASS"
    assert payload["port"] == "finbench.v1"
    assert payload["baseline_sha256"].startswith("0db3ba2b")


def test_run_recorded_val_discloses(capsys):
    code = main(["run", "--dataset", "indic-fin-v0.1.0", "--split", "val", "--mode", "recorded"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["overall_status"] == "PASS"
    assert "disclosure" in payload
    assert payload["disclosure"]["dataset_sha256"]
    assert payload["disclosure"]["denominators"]
    assert "system" in payload["disclosure"]["system_labels"]


def test_run_unsafe_exits_nonzero(capsys):
    code = main(["run", "--split", "val", "--mode", "unsafe"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 1
    assert payload["hard_safety_pass"] is False
    assert payload["overall_status"] == "FAIL"
