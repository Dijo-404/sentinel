# replay.v1 real-peer compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`  
SHA-256: `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`

## Consumed peers

| Port | Local stub | Real adapter | Fixture run | Real-peers run |
| --- | --- | --- | --- | --- |
| `evaluation.v1` | `tests/stubs/evaluation/` | `RealEvaluationAdapter` | not required | fails closed when URL absent; never fixture-fallback |
| `payment-provider.v1` | `tests/stubs/payment_provider/` | `RealPaymentProviderAdapter` | sandbox simulator only | fails closed when URL absent; never mints refunds |

## Compatibility rules

1. Real-peer mode with missing URLs returns `PEER_UNAVAILABLE` / FAIL — never silent fixture success.
2. Fixture-mode comparison evidence is labeled `evidence_mode: fixture` and is not product release evidence.
3. Production write and notification route prefixes are blocked inside the sandbox simulator guard.
4. Seed, model mode (`fake|live|absent`), and adapter presence are recorded on every `RunReport.modes`.
5. Assembly must pin compatible evaluator and simulator versions separately; this module does not import sibling packages.
