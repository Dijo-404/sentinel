"""Map authorized case order identity to provider/simulator order keys."""

from __future__ import annotations

_BOUNDARIES = ("/", ":")


class OrderReferenceError(ValueError):
    """Authorized order_reference cannot be mapped to a provider key."""


def provider_order_id(authorized_reference: str) -> str:
    """Derive bare provider order id from an authorized case ``order_reference``.

    Canonical authorized form is ``{subject_ref}/{customer_order_id}``
    (example: ``subject-a/DEMO-ORDER-42``). Colon boundary
    (``subject-a:42``) also binds. Provider and simulator keys are the
    customer-order suffix after the first ``/`` or ``:``. Bare refs pass
    through unchanged. Malformed boundaries fail closed.
    """
    if not isinstance(authorized_reference, str):
        raise OrderReferenceError("order_reference is required")
    if not authorized_reference or authorized_reference != authorized_reference.strip():
        raise OrderReferenceError("order_reference is invalid")

    positions = [authorized_reference.find(b) for b in _BOUNDARIES]
    hits = [p for p in positions if p >= 0]
    if not hits:
        return authorized_reference

    idx = min(hits)
    prefix = authorized_reference[:idx]
    suffix = authorized_reference[idx + 1 :]
    if not prefix or not suffix:
        raise OrderReferenceError("order_reference subject boundary is malformed")
    if suffix.startswith(_BOUNDARIES):
        raise OrderReferenceError("order_reference subject boundary is malformed")
    return suffix
