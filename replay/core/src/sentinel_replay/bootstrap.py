from __future__ import annotations

import os

from sentinel_replay.adapters.real_peers import RealPeerConfig
from sentinel_replay.application.service import ReplayDeps, default_deps
from sentinel_replay.domain.models import ModelMode, RunMode


def load_config_from_env() -> tuple[RunMode, ModelMode, RealPeerConfig]:
    mode_raw = os.environ.get("SENTINEL_REPLAY_MODE", "fixture")
    if mode_raw not in {"fixture", "real-peers"}:
        raise ValueError(f"unsupported SENTINEL_REPLAY_MODE: {mode_raw}")
    model_raw = os.environ.get("SENTINEL_REPLAY_MODEL_MODE", "fake")
    if model_raw not in {"fake", "live", "absent"}:
        raise ValueError(f"unsupported SENTINEL_REPLAY_MODEL_MODE: {model_raw}")
    peers = RealPeerConfig(
        evaluation_url=os.environ.get("SENTINEL_REPLAY_EVALUATION_URL") or None,
        payment_provider_url=os.environ.get("SENTINEL_REPLAY_PAYMENT_PROVIDER_URL") or None,
    )
    return mode_raw, model_raw, peers  # type: ignore[return-value]


def build_deps() -> tuple[RunMode, ReplayDeps]:
    mode, model_mode, peers = load_config_from_env()
    return mode, default_deps(peer_config=peers, model_mode=model_mode)
