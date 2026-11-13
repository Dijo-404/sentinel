"""CLI entry: migrate helper and version."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from sentinel_action_ledger import COMPONENT, CONTRACT_SHA256, CONTRACT_VERSION, __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-action-ledger")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("version")
    sub.add_parser("migrate")
    args = parser.parse_args(argv)
    if args.command == "version":
        print(f"{COMPONENT} {__version__} {CONTRACT_VERSION} {CONTRACT_SHA256}")
        return 0
    if args.command == "migrate":
        root = Path(__file__).resolve().parents[2]
        ini = root / "alembic.ini"
        env = os.environ.copy()
        if "DATABASE_URL" not in env:
            print("DATABASE_URL required", file=sys.stderr)
            return 2
        return subprocess.call(
            [sys.executable, "-m", "alembic", "-c", str(ini), "upgrade", "head"],
            cwd=str(root),
            env=env,
        )
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
