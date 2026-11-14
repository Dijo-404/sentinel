# SN-040 identity principal catalog compatibility

Pinned baseline: `sentinel.task-contracts.v1` /
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Human roles (roles.md §1.1)

| Role ID | Catalog entry | Money path |
|---|---|---|
| `customer` | existing | no |
| `operator` | existing | no |
| `supervisor` | existing | yes — sole human `financial.approval.decide` |
| `merchant` | SN-040 additive | **MUST NOT** money authority |
| `risk_officer` | SN-040 additive | **MUST NOT** money authority |
| `platform_admin` | SN-040 additive | **MUST NOT** money authority |

## Forbidden for merchant / risk_officer / platform_admin

These human roles MUST NOT receive:

- `financial.approval.decide` (or local alias `approval.decide`)
- `ledger.reserve`
- `ledger.claim_dispatch`
- `provider.refund.submit` / `provider.refund.reconcile`
- `verification.outcome.record`

Do not alias `platform_admin` → `sandbox-admin`, `merchant:approver` → `supervisor`,
or `risk_officer` → `supervisor`. Decide paths require the exact `supervisor` role.

## Peer consumers

Peers keep their own token maps. Additive catalog entries only; SN-007/009/012
route role requirements for money writes stay supervisor / workflow / dispatcher /
verifier as pinned.
