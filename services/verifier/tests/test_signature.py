"""Original-byte HMAC signature helpers."""

from sentinel_verifier.domain.signature import signature_hex, verify_signature


def test_signature_is_lowercase_hex_hmac_sha256():
    raw = b'{"event_id":"evt-1"}'
    digest = signature_hex(raw, key="demo-simulator-hmac-key")
    assert digest == digest.lower()
    assert len(digest) == 64
    assert verify_signature(raw, key="demo-simulator-hmac-key", provided=digest)
    assert not verify_signature(raw + b"x", key="demo-simulator-hmac-key", provided=digest)
    assert not verify_signature(raw, key="other-key", provided=digest)
