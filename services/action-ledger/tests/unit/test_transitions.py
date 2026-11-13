from sentinel_action_ledger.domain.errors import ConflictError, ForbiddenError
from sentinel_action_ledger.domain.transitions import assert_transition


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
