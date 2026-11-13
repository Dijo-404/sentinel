"""CLI for fixture self-check and local export preview."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .contracts import CONTRACT_VERSION, PORT, TelemetryContractError
from .run import run


def _default_input() -> dict:
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "run_input.json"
    if fixture.is_file():
        return json.loads(fixture.read_text(encoding="utf-8"))
    return {
        "contract_version": CONTRACT_VERSION,
        "run_id": "telemetry-check-1",
        "mode": "fixture",
        "input_artifacts": [],
        "parameters": {},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sentinel telemetry.v1 local checks and preview")
    parser.add_argument(
        "operation",
        choices=("check", "preview", "run"),
        help="check/run fixture self-tests; preview prints the RunReport JSON",
    )
    parser.add_argument(
        "--input",
        help="Optional RunInput JSON path; defaults to fixtures/run_input.json",
    )
    args = parser.parse_args(argv)
    try:
        if os.environ.get("TELEMETRY_CONTRACT_VERSION", CONTRACT_VERSION) != CONTRACT_VERSION:
            raise TelemetryContractError("Unsupported required contract version")
        if args.input:
            raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
        else:
            raw = _default_input()
        report = run(raw)
        print(json.dumps(report.to_dict(), sort_keys=True))
        if args.operation in ("check", "run") and report.status != "PASS":
            return 1
        return 0
    except TelemetryContractError:
        print(
            json.dumps(
                {
                    "port": PORT,
                    "error": "invalid_or_unsupported_run_input",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
        print(
            json.dumps(
                {
                    "port": PORT,
                    "error": "malformed_input_or_io_failure",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
