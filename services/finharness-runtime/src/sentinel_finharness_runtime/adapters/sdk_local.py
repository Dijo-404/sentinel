"""Local SDK-compatible read facade. No sibling package import."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finharness_runtime.domain.errors import PeerError
from sentinel_finharness_runtime.domain.models import CONTRACT_VERSION


class LocalSdkFacade:
    """finharness-sdk.v1 double: read-path composition over injected ports."""

    def __init__(self, *, indic_context: Any, evidence: Any, policy: Any) -> None:
        self._indic = indic_context
        self._evidence = evidence
        self._policy = policy

    def run_read_path(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            model = dict(self._indic.propose(request))
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("finharness-sdk.v1", "unavailable", str(exc)) from exc
        proposal = model.get("proposal")
        return {
            "contract_version": CONTRACT_VERSION,
            "outcome": model.get("outcome", "PROPOSAL"),
            "proposal": dict(proposal) if isinstance(proposal, Mapping) else {},
            "reason_codes": list(model.get("reason_codes") or []),
        }
