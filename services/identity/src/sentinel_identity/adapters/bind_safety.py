"""Refuse non-loopback HTTP bind while demo/sandbox credentials are configured."""

from __future__ import annotations

import os

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

DEMO_BEARER_TOKENS = frozenset(
    {
        "tok-workflow",
        "workflow-demo-token",
        "workflow-other-tenant-token",
        "operator-demo-token",
        "star-scope-demo-token",
        "x",
        # Portal / deploy/dev sandbox seed password (IDENTITY_DEMO_PASSWORD).
        "demo-password",
    }
)


class UnsafeBindError(RuntimeError):
    """Non-loopback listen with demo credentials."""


def is_loopback_host(host: str) -> bool:
    return host.strip().lower() in _LOOPBACK


def sandbox_public_bind_allowed() -> bool:
    """Explicit opt-in for labeled sandbox/dev-deploy hosts (never production)."""
    return os.environ.get("SENTINEL_SANDBOX_PUBLIC_BIND", "").strip() in {"1", "true", "yes"}


TokenValues = list[str] | set[str] | tuple[str, ...]


def assert_loopback_or_non_demo(host: str, token_values: TokenValues) -> None:
    if is_loopback_host(host):
        return
    if sandbox_public_bind_allowed():
        return
    offenders = sorted({t for t in token_values if not t or t in DEMO_BEARER_TOKENS})
    if not offenders:
        return
    shown = ", ".join(offenders[:8])
    suffix = "…" if len(offenders) > 8 else ""
    raise UnsafeBindError(
        f"Refusing non-loopback bind host={host!r} while demo bearer tokens "
        f"are configured: {shown}{suffix}. Use 127.0.0.1, set non-demo secrets, "
        f"or SENTINEL_SANDBOX_PUBLIC_BIND=1 for labeled sandbox/dev-deploy only."
    )
