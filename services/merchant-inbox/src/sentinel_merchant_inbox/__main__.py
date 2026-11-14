"""Run the merchant-inbox HTTP service."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

from sentinel_merchant_inbox.adapters.auth import TokenMap
from sentinel_merchant_inbox.adapters.bind_safety import (
    UnsafeBindError,
    assert_loopback_or_non_demo,
)
from sentinel_merchant_inbox.bootstrap import (
    DEFAULT_PRINCIPALS,
    DEMO_PEER_TOKEN,
    create_preview_app,
)


def main() -> None:
    host = os.environ.get("MERCHANT_INBOX_HOST", "127.0.0.1")
    port = int(os.environ.get("MERCHANT_INBOX_PORT", "8028"))
    path = Path(os.environ.get("MERCHANT_INBOX_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS)))
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    tokens = list(TokenMap.from_path(path).tokens.keys())
    tokens.append(os.environ.get("MERCHANT_INBOX_PEER_TOKEN") or DEMO_PEER_TOKEN)
    try:
        assert_loopback_or_non_demo(host, tokens)
    except UnsafeBindError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    app = create_preview_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
