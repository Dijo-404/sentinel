"""Run the policy HTTP service."""

from __future__ import annotations

import os

import uvicorn

from sentinel_policy.bootstrap import build_app


def main() -> None:
    host = os.environ.get("POLICY_HOST", "127.0.0.1")
    port = int(os.environ.get("POLICY_PORT", "8005"))
    app = build_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
