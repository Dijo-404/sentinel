from __future__ import annotations

from dataclasses import dataclass


class PeerUnavailable(RuntimeError):
    def __init__(self, peer: str, request_id: str = "harness-replay-real-peer") -> None:
        self.peer = peer
        self.payload = {
            "code": "PEER_UNAVAILABLE",
            "message": f"Required peer unavailable: {peer}",
            "request_id": request_id,
        }
        super().__init__(self.payload["message"])


@dataclass(frozen=True)
class RealPeerConfig:
    runtime_url: str | None = None
    finbench_url: str | None = None
    replay_url: str | None = None

    @property
    def runtime_configured(self) -> bool:
        return bool(self.runtime_url)

    @property
    def finbench_configured(self) -> bool:
        return bool(self.finbench_url)

    @property
    def replay_configured(self) -> bool:
        return bool(self.replay_url)


class RealRuntimeAdapter:
    """Real finharness-runtime.v1 adapter. Absent URL fails closed; never fixture-fallback."""

    def __init__(self, base_url: str | None) -> None:
        self.base_url = base_url

    def capabilities(self) -> dict:
        if not self.base_url:
            raise PeerUnavailable("finharness-runtime.v1")
        raise PeerUnavailable("finharness-runtime.v1")

    def shadow_compare(self, case_manifest: dict) -> dict:
        del case_manifest
        if not self.base_url:
            raise PeerUnavailable("finharness-runtime.v1")
        raise PeerUnavailable("finharness-runtime.v1")


class RealFinbenchAdapter:
    """Real finbench.v1 adapter. Absent URL fails closed; never fixture-fallback."""

    def __init__(self, base_url: str | None) -> None:
        self.base_url = base_url

    def capabilities(self) -> dict:
        if not self.base_url:
            raise PeerUnavailable("finbench.v1")
        raise PeerUnavailable("finbench.v1")

    def score_candidate(self, run_payload: dict) -> dict:
        del run_payload
        if not self.base_url:
            raise PeerUnavailable("finbench.v1")
        raise PeerUnavailable("finbench.v1")


class RealReplayAdapter:
    """Real replay.v1 adapter. Absent URL fails closed; never fixture-fallback."""

    def __init__(self, base_url: str | None) -> None:
        self.base_url = base_url

    def capabilities(self) -> dict:
        if not self.base_url:
            raise PeerUnavailable("replay.v1")
        raise PeerUnavailable("replay.v1")

    def compare(self, run_payload: dict) -> dict:
        del run_payload
        if not self.base_url:
            raise PeerUnavailable("replay.v1")
        raise PeerUnavailable("replay.v1")
