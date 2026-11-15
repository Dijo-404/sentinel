"""List versioned policy artifacts for admin/workflow readers."""

from __future__ import annotations

from sentinel_policy.application.ports import PolicyCatalogPort
from sentinel_policy.contracts import PolicyInputError, Principal
from sentinel_policy.domain.artifacts import PolicyArtifact

LIST_ROLES = frozenset({"platform_admin", "workflow", "sandbox-admin"})


class ListPolicies:
    def __init__(self, catalog: PolicyCatalogPort) -> None:
        self._catalog = catalog

    def __call__(self, principal: Principal) -> tuple[PolicyArtifact, ...]:
        if not LIST_ROLES.intersection(principal.roles):
            raise PolicyInputError(
                "FORBIDDEN",
                "platform_admin, workflow, or sandbox-admin required",
            )
        return self._catalog.list()
