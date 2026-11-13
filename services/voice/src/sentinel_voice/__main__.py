"""Run the voice HTTP service."""

from __future__ import annotations

import os

import uvicorn

from sentinel_voice.bootstrap import build_app


def main() -> None:
    host = os.environ.get("VOICE_HOST", "127.0.0.1")
    port = int(os.environ.get("VOICE_PORT", "8017"))
    app = build_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
