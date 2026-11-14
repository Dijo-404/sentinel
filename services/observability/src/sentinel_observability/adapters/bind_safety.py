"""Refuse non-loopback HTTP bind while demo/sandbox bearer tokens are configured."""

from __future__ import annotations

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

DEMO_BEARER_TOKENS = frozenset(
    {
        "admin-token",
        "sandbox-admin-token",
        "other-tenant-token",
        "operator-token",
    }
)


class UnsafeBindError(RuntimeError):
    """Non-loopback listen with demo credentials."""


def is_loopback_host(host: str) -> bool:
    return host.strip().lower() in _LOOPBACK


TokenValues = list[str] | set[str] | tuple[str, ...]


def assert_loopback_or_non_demo(host: str, token_values: TokenValues) -> None:
    if is_loopback_host(host):
        return
    offenders = sorted({t for t in token_values if not t or t in DEMO_BEARER_TOKENS})
    if not offenders:
        return
    shown = ", ".join(offenders[:8])
    suffix = "…" if len(offenders) > 8 else ""
    raise UnsafeBindError(
        f"Refusing non-loopback bind host={host!r} while demo bearer tokens "
        f"are configured: {shown}{suffix}. Use 127.0.0.1 or set non-demo secrets."
    )
