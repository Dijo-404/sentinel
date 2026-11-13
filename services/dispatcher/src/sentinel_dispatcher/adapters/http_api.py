"""Minimal FastAPI probe surface for dispatcher.v1 assembly."""

from __future__ import annotations

from fastapi import FastAPI

from sentinel_dispatcher.composition import capabilities


def create_app(*, mode: str = "fixture") -> FastAPI:
    if mode not in {"fixture", "real-peers"}:
        raise ValueError("mode must be fixture or real-peers")

    app = FastAPI(title="sentinel-dispatcher", version="0.1.0")
    app.state.mode = mode

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready", "mode": app.state.mode}

    @app.get("/v1/capabilities")
    def caps() -> dict[str, str]:
        return capabilities(mode=app.state.mode)

    return app
