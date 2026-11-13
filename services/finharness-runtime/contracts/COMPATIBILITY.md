# finharness-runtime.v1 real-peer compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`  
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Consumed peers

| Port | Local stub | Real adapter | Fixture run | Real-peers run |
| --- | --- | --- | --- | --- |
| `finharness-sdk.v1` | `tests/stubs/finharness_sdk.py` | `RealSdkAdapter` | local facade | fails closed when URL absent |
| `indic-context.v1` | `tests/stubs/indic_context.py` | `RealIndicContextAdapter` | fixture propose | fails closed when URL absent |
| `evidence.v1` | `tests/stubs/evidence.py` | `RealEvidenceAdapter` | fixture collect | fails closed when URL absent |
| `policy.v1` | `tests/stubs/policy.py` | `RealPolicyAdapter` | fixture evaluate | fails closed when URL absent |
| `action-ledger.v1` | `tests/stubs/action_ledger.py` | `RealLedgerAdapter` | read/reconcile only in shadow | fails closed when URL absent |
| `verifier.v1` | `tests/stubs/verifier.py` | `RealVerifierAdapter` | fixture assess | fails closed when URL absent |

## Compatibility rules

1. Real-peer mode with missing URLs returns `PeerError` / `unavailable` — never silent fixture success.
2. Shadow mode never exposes a write adapter, payment write credentials, or notification capability.
3. Shadow and reconcile paths never mint a second refund reference; reconciliation reuses the original `provider_ref`.
4. Case pins and unknown-action records survive config switch and process restart via durable store.
5. SN-009 / `action-ledger.v1` remains sole financial authority; this module owns no ledger tables.
