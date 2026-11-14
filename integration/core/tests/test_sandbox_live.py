"""Optional live real-peers journeys. Skips unless SENTINEL_V1_SANDBOX=1 and stack is up."""

from __future__ import annotations

import os

import httpx
import pytest

from sentinel_core_assembly.adapters.composition import build_peers
from sentinel_core_assembly.adapters.config import AssemblyConfig
from sentinel_core_assembly.adapters.sandbox_matrix import default_peer_endpoints, default_tokens
from sentinel_core_assembly.application.assembly import run_assembly
from sentinel_core_assembly.domain.types import CONTRACT_VERSION, ArtifactRef, RunInput

pytestmark = pytest.mark.skipif(
    os.environ.get("SENTINEL_V1_SANDBOX", "") != "1",
    reason="Set SENTINEL_V1_SANDBOX=1 with local sandbox stack running",
)


def test_live_sandbox_four_journeys() -> None:
    endpoints = default_peer_endpoints()
    # Cheap readiness: payment-provider capabilities must answer real-peers.
    provider = endpoints["payment-provider.v1"]
    try:
        caps = httpx.get(f"{provider}/v1/capabilities", timeout=2.0)
    except httpx.HTTPError as exc:
        pytest.skip(f"sandbox payment-provider not reachable: {exc}")
    if caps.status_code != 200 or caps.json().get("mode") != "real-peers":
        pytest.skip("payment-provider not in mode=real-peers")

    config = AssemblyConfig(
        mode="real-peers",
        contract_version=CONTRACT_VERSION,
        contract_sha256=AssemblyConfig.from_env({}).contract_sha256,
        peer_endpoints=endpoints,
        tokens=default_tokens(),
    )
    peers = build_peers(config)
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="live-sandbox-four",
            mode="real-peers",
            input_artifacts=(
                ArtifactRef(
                    kind="sandbox-stack",
                    uri="local://v1-sandbox",
                    sha256="0" * 64,
                    component_version="0.1.0",
                    evidence_mode="real-component",
                ),
            ),
        ),
        peers,
    )
    assert report.payment_provider == "simulator"
    assert report.path == "provider-sandbox-only"
    assert report.assembled_mvp_claimed is False
    assert report.sn009_authority_exercised is False
    assert report.status == "PASS", report.as_dict()
