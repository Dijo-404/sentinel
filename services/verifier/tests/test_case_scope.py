"""Principal case scope: empty deny, star allow."""

from __future__ import annotations

from sentinel_verifier.domain.types import Principal


def test_empty_case_ids_deny():
    principal = Principal("p", "tenant", ("workflow",), (), ())
    assert principal.allows_case("case-demo-42") is False


def test_star_allows_any_case():
    principal = Principal("p", "tenant", ("workflow",), (), ("*",))
    assert principal.allows_case("case-any") is True


def test_explicit_case_allowlist():
    principal = Principal("p", "tenant", ("workflow",), (), ("case-demo-42",))
    assert principal.allows_case("case-demo-42") is True
    assert principal.allows_case("case-other") is False
