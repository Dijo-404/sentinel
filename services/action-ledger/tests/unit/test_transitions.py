from sentinel_action_ledger.domain.errors import ConflictError, ForbiddenError
from sentinel_action_ledger.domain.transitions import assert_transition
from sentinel_action_ledger.domain.types import Principal


def test_dispatcher_cannot_confirm_provider():
    try:
        assert_transition("PENDING", "PROVIDER_CONFIRMED", roles=("dispatcher",))
        raise AssertionError("expected forbidden")
    except ForbiddenError:
        pass


def test_regressive_terminal_rejected():
    try:
        assert_transition("FAILED_FINAL", "PENDING", roles=("dispatcher",))
        raise AssertionError("expected conflict")
    except ConflictError as exc:
        assert exc.code == "INVALID_TRANSITION"


def test_allows_case_empty_denies_wildcard_allows():
    empty = Principal("p", "t", ("workflow",), (), ())
    assert empty.allows_case("case-demo-42") is False
    wild = Principal("p", "t", ("dispatcher",), (), ("*",))
    assert wild.allows_case("any-case") is True
    scoped = Principal("p", "t", ("workflow",), (), ("case-demo-42",))
    assert scoped.allows_case("case-demo-42") is True
    assert scoped.allows_case("other") is False
