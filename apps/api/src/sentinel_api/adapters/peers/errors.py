"""Map peer failures without silent fixture fallback."""

from __future__ import annotations

from sentinel_api.domain.types import DomainError


class PeerError(DomainError):
    pass


def unavailable(peer: str) -> PeerError:
    return PeerError("PEER_UNAVAILABLE", f"Required peer unavailable: {peer}", 503)


def malformed(peer: str) -> PeerError:
    return PeerError("PEER_MALFORMED", f"Peer returned malformed payload: {peer}", 502)


def unauthorized(peer: str) -> PeerError:
    return PeerError("PEER_UNAUTHORIZED", f"Peer rejected authorization/scope: {peer}", 403)
