"""Composition root: wire config into use cases."""

from __future__ import annotations

import json
import os
from pathlib import Path

from sentinel_release_mvp.adapters.peer_stubs import StubPeerRunner, default_stubs
from sentinel_release_mvp.adapters.real_peer import RealPeerRunner, runners_from_config
from sentinel_release_mvp.application.ports import PeerRunner
from sentinel_release_mvp.contracts import REQUIRED_PORTS

MODULE_ROOT = Path(__file__).resolve().parents[2]


def module_root() -> Path:
    return MODULE_ROOT


def contracts_dir() -> Path:
    return MODULE_ROOT / "contracts"


def load_peer_config(path: Path | None = None) -> dict[str, str]:
    env_path = os.environ.get("RELEASE_MVP_PEER_CONFIG")
    cfg_path = path or (Path(env_path) if env_path else MODULE_ROOT / "peers.json")
    if not cfg_path.is_file():
        return {}
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("peers.json must be an object of port -> endpoint")
    return {str(k): str(v) for k, v in data.items()}


def build_peers(*, mode: str, stub_case: str = "valid") -> dict[str, PeerRunner]:
    if mode == "fixture":
        return dict(default_stubs(case=stub_case))  # type: ignore[arg-type]
    config = load_peer_config()
    peers: dict[str, PeerRunner] = {}
    for port in REQUIRED_PORTS:
        endpoint = config.get(port, "")
        if not endpoint:
            # Explicit missing peer — RealPeerRunner raises PEER_UNAVAILABLE.
            peers[port] = RealPeerRunner(port, "")
        else:
            peers[port] = RealPeerRunner(port, endpoint)
    return peers


def stub_runner(port: str, case: str) -> StubPeerRunner:
    return StubPeerRunner(port, case=case)  # type: ignore[arg-type]


def real_runners(config: dict[str, str]) -> dict[str, RealPeerRunner]:
    return runners_from_config(config)
