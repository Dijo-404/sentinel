# SN-029 — merchant refund request workflow

Scaffold for `merchant-refunds.v1`. Implementation is the owned task deliverable; this guide is not a running service.

**Owned root:** `services/merchant-refunds/` · **Branch:** `feat/sn-029-merchant-refunds`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Standalone setup and checks

```sh
make -C services/merchant-refunds check
```

The check target is a required deliverable of SN-029. It is not implemented yet. Use local peer stubs only; no sibling Sentinel services or real payment credentials.

## Scope

See the published GitHub issue for acceptance criteria, consumed ports and independence rules. Financial writes remain on SN-009 / SN-010; this module must not create a second executor or ledger.
