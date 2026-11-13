from __future__ import annotations

import os

from sentinel_harness_replay.adapters.real_peers import RealPeerConfig
from sentinel_harness_replay.application.service import HarnessReplayDeps, default_deps
from sentinel_harness_replay.domain.models import ModelMode, RunMode


def load_config_from_env() -> tuple[RunMode, ModelMode, RealPeerConfig]:
    mode_raw = os.environ.get("SENTINEL_HARNESS_REPLAY_MODE", "fixture")
    if mode_raw not in {"fixture", "real-peers"}:
        raise ValueError(f"unsupported SENTINEL_HARNESS_REPLAY_MODE: {mode_raw}")
    model_raw = os.environ.get("SENTINEL_HARNESS_REPLAY_MODEL_MODE", "fake")
    if model_raw not in {"fake", "live", "absent"}:
        raise ValueError(f"unsupported SENTINEL_HARNESS_REPLAY_MODEL_MODE: {model_raw}")
    peers = RealPeerConfig(
        runtime_url=os.environ.get("SENTINEL_HARNESS_RUNTIME_URL") or None,
        finbench_url=os.environ.get("SENTINEL_HARNESS_FINBENCH_URL") or None,
        replay_url=os.environ.get("SENTINEL_HARNESS_REPLAY_PEER_URL") or None,
    )
    return mode_raw, model_raw, peers  # type: ignore[return-value]


def build_deps() -> tuple[RunMode, HarnessReplayDeps]:
    mode, model_mode, peers = load_config_from_env()
    return mode, default_deps(peer_config=peers, model_mode=model_mode)
