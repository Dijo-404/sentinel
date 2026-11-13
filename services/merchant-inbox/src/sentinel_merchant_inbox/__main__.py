"""Run the merchant-inbox HTTP service."""

from __future__ import annotations

import os

import uvicorn

from sentinel_merchant_inbox.bootstrap import create_preview_app


def main() -> None:
    host = os.environ.get("MERCHANT_INBOX_HOST", "127.0.0.1")
    port = int(os.environ.get("MERCHANT_INBOX_PORT", "8028"))
    app = create_preview_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
