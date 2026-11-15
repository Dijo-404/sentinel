# Dataset inventory (2026-11-15)

| Scenario | Source | Count | Notes |
|---|---|---:|---|
| Status observation (missing/invalid order) | Paytm staging live (`334`) | 5 | Signed status responses captured under `fixtures/status-*` |
| Initiate attempt | Paytm staging live (`239`) | 1 | No `txnToken`; shared MID cannot create payments |
| Refund apply / status | Paytm staging live (`335`) | 2 | Invalid merchant Id on refund hosts |
| Successful payment | Synthetic simulator | 3 | `PAYTM-TXN-A1/A2`, `PAYTM-TXN-MISMATCH` in `paytm_staging` seed |
| Failed payment (shaped) | Synthetic + live status shape | 1+5 | Seed `PAYTM-TXN-FAIL-001` + live `334` fixtures |
| Refund request/status (shaped) | Synthetic simulator | 1 | `SNT-REF-PAYTM-001` PENDING |
| Duplicate complaint variants | FinBench synthetic | 7 | `paytm_dup_010` group, one split |
| Merchant mismatch | FinBench synthetic | 2 | `paytm_mismatch_011` |
| Unauthorized refund | FinBench synthetic | 2 | `paytm_unauthorized_012` |
| Timeout / pending credit | Existing simulator faults | use built-ins | `timeout-after-accept`, `refund_pending` packs |

**Blocker for TXN_SUCCESS / real refunds:** shared test MID authenticates status but rejects initiate (`239`) and refund (`335`). Replace `.env` with a dashboard-generated test MID, re-run `capture.py initiate` + checkout + `refund-apply`, then refresh seed fixtures.

**Live read path:** `provider_bridge.py` → evidence `real-peers`.
