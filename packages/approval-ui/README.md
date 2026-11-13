# SN-013 — Independently previewable approval UI package

**State:** implemented module with standalone checks. Real case-api / action-ledger peers remain unverified until assembly.

**Owned root:** `packages/approval-ui/`  
**Branch:** `feat/sn-013-approval-ui`  
**Produces:** `approval-ui.v1`  
**Consumes (via injected client / local stubs):** `case-api.v1`, `action-ledger.v1`

Contract baseline: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Outcome

Embeddable typed approval/evidence React component with its own Vite preview and an injected authorized `decide` client. Models never approve: the UI only posts supervisor `DecisionRequest` values built from the supplied action digest, case revision, policy version, and expiry.

## Setup

```sh
make -C packages/approval-ui setup
# or: npm ci
```

Requires Node.js 20+.

## Check

```sh
make -C packages/approval-ui check
```

Runs `tsc --noEmit` and Vitest (jsdom browser checks + stub/adapter tests). Uses only this package, fixtures under `fixtures/`, and stubs under `tests/stubs/`. No sibling services or web shell.

## Preview

```sh
make -C packages/approval-ui preview
```

Opens the standalone fixture preview (no web shell). Virtual clock `2026-11-13T12:00:00Z`. Decision client is the local `case-api.v1` valid stub.

## Public boundary (`approval-ui.v1`)

```ts
import {
  ApprovalPanel,
  createCaseApiDecideClient,
  createActionLedgerDecideClient,
} from "sentinel-approval-ui";

<ApprovalPanel
  case={caseRecord}
  action={actionRecord}
  evidence={evidence}
  reviewerId={principal.principal_id}
  decisionExpiresAt="2026-11-13T14:00:00Z"
  decide={injectedDecide}
  onRefresh={...}
  onConflict={...}
/>
```

- Fixture mode: wire `tests/stubs` or any in-process double.
- Real-peer mode: `createCaseApiDecideClient` / `createActionLedgerDecideClient` with base URL + bearer token. Failures stay visible; no silent fixture fallback.

## Layout

| Path | Role |
| --- | --- |
| `src/domain/` | Wire types, view-model rules, error mapping |
| `src/application/` | `DecideClient` port and submit use case |
| `src/adapters/` | Real-peer HTTP clients |
| `src/ui/` | Accessible `ApprovalPanel` |
| `src/preview/` | Standalone preview entry |
| `fixtures/` | Synthetic preview bundle (labeled fixture) |
| `contracts/` | Port snapshots + baseline hash |
| `tests/stubs/` | `case-api.v1` and `action-ledger.v1` doubles |

## Acceptance coverage

1. Preview fixture shows amount `150000` INR / `TXN-B`, policy `demo-policy-v1`, evidence ages, digest `d5ce68ac…`, expiry, reviewer `supervisor-demo-1`; approve/reject posts that digest/revision.
2. Expired, stale, unauthorized, cross-tenant, and HTTP 409 responses render `role="alert"` and emit refresh/conflict events without a live API.
3. `make check` is module-local.

## Evidence limits

- Component checks: fixture stubs + simulated HTTP.
- Real-peer assembly with live case-api/ledger: **UNVERIFIED**.
- Not product-release evidence.
