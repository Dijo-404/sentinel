"""Equal amounts alone never prove duplication; independent facts do."""

from sentinel_evidence.domain.reconcile import reconcile_codes
from sentinel_evidence.domain.types import Order, Payment, Refund


def _pay(ref: str, amount: int = 150000) -> Payment:
    return Payment(
        ref, "DEMO-ORDER-42", "subj-demo-1", "CAPTURED", amount, "INR", "merchant-demo-1"
    )


def test_equal_amounts_alone_never_duplicate():
    codes = reconcile_codes(
        payments=(_pay("TXN-A"), _pay("TXN-B")),
        order=Order("DEMO-ORDER-42", "subj-demo-1", 2, False, True),
        refunds=(),
        stale=False,
        conflicting=False,
    )
    assert "EQUAL_AMOUNTS_INSUFFICIENT" in codes
    assert "DUPLICATE_PAYMENT" not in codes
    assert "MERCHANT_CONFIRMED_DUPLICATE" not in codes


def test_duplicate_requires_distinct_merchant_and_underfulfillment():
    codes = reconcile_codes(
        payments=(_pay("TXN-A"), _pay("TXN-B")),
        order=Order("DEMO-ORDER-42", "subj-demo-1", 1, True, True),
        refunds=(),
        stale=False,
        conflicting=False,
    )
    assert "DISTINCT_TRANSACTION_REFS" in codes
    assert "MERCHANT_CONFIRMED_DUPLICATE" in codes
    assert "ORDER_UNDERFULFILLED" in codes
    assert "DUPLICATE_PAYMENT" in codes
    assert "EQUAL_AMOUNTS_INSUFFICIENT" not in codes


def test_distinct_transactions_without_merchant_confirmation():
    codes = reconcile_codes(
        payments=(_pay("TXN-A"), _pay("TXN-B")),
        order=Order("DEMO-ORDER-42", "subj-demo-1", 1, False, True),
        refunds=(),
        stale=False,
        conflicting=False,
    )
    assert "DISTINCT_TRANSACTION_REFS" in codes
    assert "ORDER_UNDERFULFILLED" in codes
    assert "DUPLICATE_PAYMENT" not in codes
    assert "EQUAL_AMOUNTS_INSUFFICIENT" in codes


def test_refund_and_stale_codes():
    codes = reconcile_codes(
        payments=(_pay("TXN-B"),),
        order=Order("DEMO-ORDER-42", "subj-demo-1", 1, False, True),
        refunds=(Refund("a1", "r1", "TXN-B", 150000, "INR", "PENDING"),),
        stale=True,
        conflicting=False,
    )
    assert "STALE_PROVIDER_SNAPSHOT" in codes
    assert "REFUND_PENDING" in codes
