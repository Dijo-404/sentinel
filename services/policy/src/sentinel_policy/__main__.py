"""Run the policy HTTP service."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

from sentinel_policy.adapters.auth import TokenMap
from sentinel_policy.adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from sentinel_policy.bootstrap import DEFAULT_PRINCIPALS, build_app


def main() -> None:
    host = os.environ.get("POLICY_HOST", "127.0.0.1")
    port = int(os.environ.get("POLICY_PORT", "8005"))
    path = Path(os.environ.get("POLICY_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS)))
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    try:
        assert_loopback_or_non_demo(host, TokenMap.from_path(path).tokens.keys())
    except UnsafeBindError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    app = build_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
