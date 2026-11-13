# SN-012 — Customer and operator web shell

**State:** implemented module with local fixture checks. Assembled real-peer product evidence is unverified.

**Owned root:** `apps/web/`  
**Branch:** `feat/sn-012-ui-shell`  
**Produces:** `web-shell.v1`  
**Consumes:** `case-api.v1`, `approval-ui.v1`, optional `voice.v1`  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`

## Outcome

Text intake, case timeline, operator queue, and evidence pages. Local case-api stub for standalone work. Documented approval-ui and voice component slots render **local substitutes** (no deep import of sibling packages). Voice is disabled by default. Financial authority stays on the server; the UI masks PII and payment identifiers.

## Standalone setup

Requires Node.js 20+.

```sh
cd apps/web
cp .env.example .env   # optional; defaults to fixture mode
make check             # npm ci + tsc + vitest
```

Preview (after check/build):

```sh
make -C apps/web preview
# or: npm run dev
```

Open `http://localhost:3012/intake` and `http://localhost:3012/ops`.

## Configuration

See `.env.example`.

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SHELL_MODE` | `fixture` (default) or `real-peers` |
| `NEXT_PUBLIC_VOICE_ENABLED` | `false` by default |
| `CASE_API_BASE_URL` | Required in real-peers mode |
| `CASE_API_BEARER_TOKEN` | Required in real-peers mode |

Real-peer failures are visible (`PEER_UNAVAILABLE`, `FORBIDDEN`, `MALFORMED_PEER_RESPONSE`). The shell never silently switches to fixtures.

## Layout

- `src/domain/` — wire types, masking, status labels (framework-free)
- `src/application/ports.ts` — CaseClient / slot ports
- `src/adapters/` — fixture + real-peer clients, composition
- `src/slots/` — local approval-ui / voice substitutes
- `src/app/` — Next.js routes
- `tests/stubs/` — case-api, approval-ui, voice doubles (valid / unavailable / malformed / unauthorized)
- `contracts/` — snapshots, fixtures, compatibility checklist

## Pages

| Route | Role |
| --- | --- |
| `/intake` | Customer text intake (+ disabled voice slot) |
| `/cases/[caseId]` | Case timeline |
| `/ops` | Operator queue |
| `/ops/cases/[caseId]/evidence` | Evidence + approval slot |

Status chips use exact labels for **Pending**, **Provider confirmed**, **Credit confirmed** / **Credit pending**, and **Escalated**.

## Checks observed

```sh
make -C apps/web check
```

Independence: installs only `apps/web` dependencies; uses local stubs under `tests/stubs/`; no sibling Sentinel services required.

Root `make check` validates repository metadata only.

## Evidence labels

| Dimension | This module check |
| --- | --- |
| Component under test | Real web-shell implementation |
| Case API peer | Local fixture stub |
| Approval UI / voice | Local substitutes |
| Payment provider | N/A (UI only) |
| Model/voice live | Off |

Assembled real-peer integration remains **unverified** until owner assembly.
