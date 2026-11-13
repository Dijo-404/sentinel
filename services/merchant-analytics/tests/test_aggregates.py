"""Deterministic fixture yields expected MerchantMetrics fields."""

from __future__ import annotations

from constants import EXPECTED, WINDOW
from sentinel_merchant_analytics.adapters.fixture_peers import (
    FixtureCaseApi,
    FixtureEvidence,
    load_fixture_cases,
    load_fixture_refunds,
)
from sentinel_merchant_analytics.application.get_metrics import GetMerchantMetrics
from sentinel_merchant_analytics.domain.aggregates import compute_metrics, format_exception_rate
from sentinel_merchant_analytics.domain.types import Principal


def test_format_exception_rate_fixed_decimal():
    assert format_exception_rate(4, 10) == "0.4000"
    assert format_exception_rate(0, 0) == "0.0000"
    assert format_exception_rate(1, 3) == "0.3333"


def test_compute_metrics_matches_contract_fixture():
    metrics = compute_metrics(
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo-1",
        window_start=WINDOW["window_start"],
        window_end=WINDOW["window_end"],
        cases=load_fixture_cases(),
        refunds=load_fixture_refunds(),
    )
    wire = metrics.to_wire()
    assert wire["exception_rate"] == EXPECTED["exception_rate"]
    assert wire["unresolved_minor"] == EXPECTED["unresolved_minor"]
    assert wire["refund_aging_buckets"] == EXPECTED["refund_aging_buckets"]
    assert wire["median_handling_seconds"] == EXPECTED["median_handling_seconds"]
    assert wire["top_causes"] == EXPECTED["top_causes"]
    assert wire["currency"] == "INR"


def test_use_case_via_valid_stubs():
    principal = Principal(
        "op-1",
        "tenant-demo",
        ("operator",),
        ("subj-demo-1",),
        ("*",),
        ("merchant-demo-1",),
    )
    usecase = GetMerchantMetrics(FixtureCaseApi("valid"), FixtureEvidence("valid"))
    metrics = usecase(
        principal,
        merchant_ref="merchant-demo-1",
        window_start=WINDOW["window_start"],
        window_end=WINDOW["window_end"],
    )
    assert metrics.to_wire() == EXPECTED
