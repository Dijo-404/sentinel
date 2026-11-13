"""CLI entry for local preview helpers."""

from __future__ import annotations

import argparse

from sentinel_api import CONTRACT_HASH, CONTRACT_VERSION, __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-api")
    parser.add_argument("command", choices=["version", "contract"])
    args = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    print(f"{CONTRACT_VERSION} {CONTRACT_HASH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
