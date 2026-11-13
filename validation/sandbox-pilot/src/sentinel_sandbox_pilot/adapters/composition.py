"""Single composition entry: wire fixture reference peers or HTTP real-peer probes."""

from __future__ import annotations

import httpx

from sentinel_sandbox_pilot.adapters.config import PilotConfig
from sentinel_sandbox_pilot.adapters.reference import HttpPeerBundle, ReferenceBundle
from sentinel_sandbox_pilot.application.ports import ValidationPeers
from sentinel_sandbox_pilot.domain.types import CONTRACT_SHA256, CONTRACT_VERSION


def build_peers(config: PilotConfig) -> ValidationPeers:
    if config.contract_version != CONTRACT_VERSION:
        raise ValueError("CONTRACT_VERSION_MISMATCH")
    if config.contract_sha256 != CONTRACT_SHA256:
        raise ValueError("CONTRACT_HASH_MISMATCH")
    if config.mode == "fixture":
        return ReferenceBundle()
    if config.mode == "real-peers":
        client = httpx.Client(timeout=2.0)
        return HttpPeerBundle(endpoints=dict(config.peer_endpoints), client=client)
    raise ValueError("UNSUPPORTED_MODE")
