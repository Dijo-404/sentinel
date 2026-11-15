# Paytm staging sandbox (Sentinel)

Capture authorized Paytm **staging** status/refund observations, normalize fixtures, and
expose a `payment-provider.v1` bridge for evidence `real-peers` reads.

Not a second financial executor. Ledger-controlled refunds stay in Sentinel's dispatcher
when a write-capable MID exists.

Guide: [docs/paytm-testdata-integration.md](../../docs/paytm-testdata-integration.md) ·
Inventory: [DATASET.md](DATASET.md)

## Setup

```bash
cd integration/paytm-sandbox
cp .env.example .env
# Quote the merchant key — dotenv treats bare # as a comment:
# PAYTM_MERCHANT_KEY="your-key-with-#chars"
uv sync
```

Never commit `.env`. Merchant keys stay local.

## Commands

```bash
uv run python capture.py probe
uv run python capture.py status ORDER_ID
uv run python capture.py initiate --amount 10.00
uv run python capture.py refund-apply --order-id OID --txn-id TXN --amount 5.00
uv run python capture.py refund-status --order-id OID --ref-id REF
uv run python capture.py batch-status OID1 OID2 OID3
uv run python capture.py manifest
uv run pytest -q
```

| Path          | Contents                               |
| ------------- | -------------------------------------- |
| `.raw/`       | Ignored original provider bytes        |
| `fixtures/`   | Redacted observations (safe to commit) |
| `normalized/` | Manifest + payment/refund lists        |

## Observed capability (shared test MID)

Against `wkyQgn37386655602538` on 2026-11-15:

| API                  | Result                                           |
| -------------------- | ------------------------------------------------ |
| Transaction status   | Works (signed responses; missing orders → `334`) |
| Initiate transaction | `239` System Error — no `txnToken`               |
| Refund apply         | `335` Invalid merchant Id                        |

This MID yields **actual staging status observations**, not new successful payments or
refunds. Use a dashboard-generated test MID (or mentor merchant) for `TXN_SUCCESS` /
refund captures. Until then, Sentinel uses captured status fixtures plus clearly labeled
synthetic Paytm-shaped simulator/FinBench seeds.

## Live staging read bridge

```bash
uv run uvicorn provider_bridge:app --host 127.0.0.1 --port 8026
```

Point evidence at the bridge:

```bash
EVIDENCE_MODE=real-peers
PAYMENT_PROVIDER_BASE_URL=http://127.0.0.1:8026
PAYMENT_PROVIDER_TOKEN=tok-workflow
SENTINEL_EVIDENCE_ALLOW_MEMORY=1   # local only
```

Bridge maps Paytm Transaction Status → `payment-provider.v1`. Order fulfillment fields are
local defaults (Paytm status has no merchant order book). Refund list stays empty unless a
refId store is added. Fail closed on scope/signature problems.

## Sentinel wiring

| Piece              | How                                                                                                 |
| ------------------ | --------------------------------------------------------------------------------------------------- |
| Evidence live read | `real-peers` → this bridge ([services/evidence/.env.example](../../services/evidence/.env.example)) |
| Simulator replay   | `POST /v1/admin/seeds/paytm_staging` (opt-in pack; not default seed)                                |
| FinBench groups    | `paytm_dup_010`, `paytm_mismatch_011`, `paytm_unauthorized_012`                                     |
