from sentinel_action_ledger.domain.errors import ConflictError
from sentinel_action_ledger.domain.money import PaymentBalance, apply_reserve


def test_reserve_blocks_overrun():
    balance = PaymentBalance(150000, 100000, 40000, 10000)
    try:
        apply_reserve(balance, 1)
        raise AssertionError("expected conflict")
    except ConflictError as exc:
        assert exc.code == "INSUFFICIENT_ELIGIBLE"


def test_reserve_exact_remaining():
    balance = PaymentBalance(150000, 0, 0, 0)
    updated = apply_reserve(balance, 150000)
    assert updated.remaining() == 0
