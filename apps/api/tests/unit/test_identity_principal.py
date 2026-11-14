"""Identity session projection maps to Principal; unknown falls through."""

from sentinel_api.adapters.http.auth import CompositePrincipalResolver, TokenMap
from sentinel_api.adapters.identity.fixture import (
    FixtureIdentityPrincipalAdapter,
    principal_from_session_projection,
)
from sentinel_api.domain.types import DomainError, Principal


def test_principal_from_session_projection_ignores_merchant_refs():
    principal = principal_from_session_projection(
        {
            "principal_id": "customer-a",
            "tenant_id": "tenant-demo",
            "roles": ["customer"],
            "subject_refs": ["subject-a"],
            "case_ids": [],
            "merchant_refs": ["merchant-x"],
        }
    )
    assert principal == Principal(
        principal_id="customer-a",
        tenant_id="tenant-demo",
        roles=("customer",),
        subject_refs=("subject-a",),
        case_ids=(),
    )


def test_composite_prefers_identity_session_over_token_map():
    identity = FixtureIdentityPrincipalAdapter.from_mapping(
        {
            "sess-op": {
                "principal_id": "operator-session",
                "tenant_id": "tenant-demo",
                "roles": ["operator"],
                "subject_refs": [],
                "case_ids": [],
            }
        }
    )
    tokens = TokenMap.from_mapping(
        {
            "sess-op": {
                "principal_id": "operator-opaque",
                "tenant_id": "tenant-demo",
                "roles": ["operator"],
                "subject_refs": [],
                "case_ids": [],
            },
            "tok-workflow": {
                "principal_id": "workflow-1",
                "tenant_id": "tenant-demo",
                "roles": ["workflow"],
                "subject_refs": [],
                "case_ids": ["*"],
            },
        }
    )
    resolver = CompositePrincipalResolver(identity=identity, tokens=tokens)
    asserted = resolver.resolve("Bearer sess-op")
    assert asserted.principal_id == "operator-session"
    service = resolver.resolve("Bearer tok-workflow")
    assert service.principal_id == "workflow-1"


def test_composite_rejects_unknown_bearer():
    resolver = CompositePrincipalResolver(
        identity=FixtureIdentityPrincipalAdapter.from_mapping({}),
        tokens=TokenMap.from_mapping({}),
    )
    try:
        resolver.resolve("Bearer missing")
        raise AssertionError("expected DomainError")
    except DomainError as exc:
        assert exc.http_status == 401
        assert exc.code == "UNAUTHORIZED"
