"""Refuse non-loopback HTTP bind while demo/sandbox bearer tokens are configured."""

from __future__ import annotations

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

DEMO_BEARER_TOKENS = frozenset(
    {
        "tok-case-api",
        "tok-workflow",
        "tok-verifier",
        "tok-merchant",
        "tok-risk-officer",
        "tok-platform-admin",
        "token-case-api-demo",
        "token-workflow-demo",
        "token-operator-demo",
        "token-merchant",
        "token-risk-officer",
        "token-platform-admin",
        # Fixture identity session credentials (apps/api/fixtures/identity_sessions.json).
        "sess-customer-a",
        "sess-operator-1",
        "sess-operator-2",
        "sess-supervisor-1",
        "sess-merchant-1",
        "sess-risk-officer-1",
        "sess-platform-admin-1",
    }
)


class UnsafeBindError(RuntimeError):
    """Non-loopback listen with demo credentials."""


def is_loopback_host(host: str) -> bool:
    return host.strip().lower() in _LOOPBACK


def is_demo_bearer_token(token: str) -> bool:
    if not token:
        return True
    if token in DEMO_BEARER_TOKENS:
        return True
    # Any fixture session/BFF double credential uses the sess- prefix.
    return token.startswith("sess-")


TokenValues = list[str] | set[str] | tuple[str, ...]


def assert_loopback_or_non_demo(
    host: str,
    token_values: TokenValues,
    *,
    identity_sessions: bool = False,
) -> None:
    if is_loopback_host(host):
        return
    if identity_sessions:
        raise UnsafeBindError(
            f"Refusing non-loopback bind host={host!r} while identity session "
            f"projection is enabled. Use 127.0.0.1 or disable IDENTITY_BASE_URL."
        )
    offenders = sorted({t for t in token_values if is_demo_bearer_token(t)})
    if not offenders:
        return
    shown = ", ".join(offenders[:8])
    suffix = "…" if len(offenders) > 8 else ""
    raise UnsafeBindError(
        f"Refusing non-loopback bind host={host!r} while demo bearer tokens "
        f"are configured: {shown}{suffix}. Use 127.0.0.1 or set non-demo secrets."
    )
