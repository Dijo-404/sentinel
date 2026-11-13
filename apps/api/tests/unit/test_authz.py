"""Authz: empty case scope denies for workflow/verifier; wildcard grants."""

from sentinel_api.application.authz import can_access_case
from sentinel_api.domain.types import Principal


def _principal(*, roles: tuple[str, ...], case_ids: tuple[str, ...] = ()) -> Principal:
    return Principal(
        principal_id="p1",
        tenant_id="tenant-demo",
        roles=roles,
        subject_refs=(),
        case_ids=case_ids,
    )


def test_workflow_empty_case_ids_deny():
    principal = _principal(roles=("workflow",), case_ids=())
    assert not can_access_case(
        principal, tenant_id="tenant-demo", case_id="case-1", subject_ref="s1"
    )


def test_workflow_wildcard_allows_any_case():
    principal = _principal(roles=("workflow",), case_ids=("*",))
    assert can_access_case(principal, tenant_id="tenant-demo", case_id="case-any", subject_ref="s1")


def test_verifier_explicit_case_only():
    principal = _principal(roles=("verifier",), case_ids=("case-1",))
    assert can_access_case(principal, tenant_id="tenant-demo", case_id="case-1", subject_ref="s1")
    assert not can_access_case(
        principal, tenant_id="tenant-demo", case_id="case-2", subject_ref="s1"
    )
