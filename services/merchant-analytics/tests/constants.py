"""Shared fixture constants for merchant-analytics tests."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "contracts" / "expected-metrics.json").read_text(encoding="utf-8"))
WINDOW = {
    "window_start": EXPECTED["window_start"],
    "window_end": EXPECTED["window_end"],
}
TOKENS = (
    "operator-token=op-1|tenant-demo|operator|subj-demo-1|*|merchant-demo-1;"
    "supervisor-token=sup-1|tenant-demo|supervisor|subj-demo-1|*|merchant-demo-1;"
    "other-merchant-token=op-2|tenant-demo|operator|subj-demo-1|*|merchant-other;"
    "customer-token=cust-1|tenant-demo|customer|subj-demo-1|case-m-01|merchant-demo-1"
)
