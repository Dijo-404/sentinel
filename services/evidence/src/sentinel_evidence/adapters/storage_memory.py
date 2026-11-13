"""In-process evidence store for unit/API tests without PostgreSQL."""

from __future__ import annotations

from ..domain.types import CollectRequest, EvidenceBundle, Principal


class MemoryEvidenceStore:
    def __init__(self) -> None:
        self._bundles: dict[tuple[str, str], EvidenceBundle] = {}

    def save_bundle(
        self,
        *,
        principal: Principal,
        request: CollectRequest,
        bundle: EvidenceBundle,
    ) -> EvidenceBundle:
        del request
        self._bundles[(principal.tenant_id, bundle.case_id)] = bundle
        return bundle

    def get_bundle(self, *, principal: Principal, case_id: str) -> EvidenceBundle | None:
        return self._bundles.get((principal.tenant_id, case_id))
