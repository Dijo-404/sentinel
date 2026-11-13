"""Run the merchant settlement HTTP service."""

from __future__ import annotations

import os

import uvicorn

from sentinel_merchant_settlement.bootstrap import build_app


def main() -> None:
    host = os.environ.get("MERCHANT_SETTLEMENT_HOST", "127.0.0.1")
    port = int(os.environ.get("MERCHANT_SETTLEMENT_PORT", "8027"))
    app = build_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
