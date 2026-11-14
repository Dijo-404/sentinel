# Portal completion — DB-backed stubs + new ops/intel peers + money-path assembly

**Date:** 2026-11-15  
**Status:** approved 2026-11-15 — human: proceed with implementation plan and subagents  
**Scope:** multi-module program (not a single owned root)

## Intent

Finish the Mercury portal surface so every current “Not available yet” nav item is a real product screen backed by **PostgreSQL through HTTP peers**, not React fixture tables. Close the known shell limits: real-peers to live case-api, **real `packages/approval-ui` (SN-013)** on supervisor decide, **voice on and wired (SN-017 + Sarvam)**, and a runnable intake → ledger → dispatcher → simulator → verifier journey. Where no peer exists today (Assistant, Knowledge, AI ops), **build new DB-backed services**. For Evaluations and Observability, **extend existing contract owners** with scalable HTTP+DB surfaces (see decisions) — do not mint a second evaluation/telemetry authority.

Why now: web + case-api already run locally, but most nav is shell-only and fixture mode hides the live API. The owner wants one coherent sandbox product: seed the DB, click every portal page, see only data that came from the database.

## Goals

1. Replace every stub page listed below with a working UI that loads via BFF → peer → DB (or returns a clear peer/DB error).
2. **No mock/fixture rows rendered as product data.** Sandbox **seed scripts** write synthetic rows into each service’s Postgres; APIs read those rows. UI never invents demo tables client-side.
3. Default local product mode for this program: `real-peers` (web + peers). Fixture mode remains for module-local `make check` only, not for the assembled demo.
4. Wire existing peers where they already exist (merchant-*, risk, identity, case-api, ledger, settlement, analytics).
5. **Evaluations (SN-016):** extend `evals/core` so it remains the sole `evaluation.v1` owner and gains optional **HTTP + Postgres persistence** for `RunReport` storage/query (CLI/CI runner and portal share one authority). Do not add a competing `services/evaluations` contract.
6. **Observability (SN-015 line):** keep `packages/telemetry` as the redacting SDK/`telemetry.v1` types; add **`services/observability`** as the scalable HTTP+DB query/ingest API for admin dashboards (consumes telemetry contract types; never replaces financial audit).
7. New independent services (own root, lockfile, migrations, `make check`) for:
   - **assistant** — persisted threads/messages (customer + operator)
   - **knowledge** — articles/search for operator knowledge base
   - **ops-activity** — activity feed (operator); may project from case events + local audit table
   - **platform-ai** — admin AI config/run metadata (no money authority)
8. **Approvals:** supervisor UI uses real `packages/approval-ui` (SN-013); remove local substitute from the assembled real-peers path. Digest binding and ledger decide stay server-side.
9. **Voice:** turn on and wire `services/voice` (SN-017) + web `voice.v1` slot. Live Sarvam credentials live only in ignored module env (`SARVAM_*`); `make check` must still pass with recorded/fixture audio and **without** requiring live credentials. Opt-in flag remains; product demo sets voice enabled.
10. Close money-path honesty: assembled sandbox can exercise intake → SN-009 → dispatcher → simulator → verifier with `path` labels per sandbox matrix; still no live payment rails.
11. Keep SN-009 sole financial authority; models/assistants/voice propose or capture text only.

## Stub inventory (must leave stub state)

| Portal | Routes |
| --- | --- |
| Operator / Supervisor | Activity, Knowledge, Messages, Assistant, Escalations, History, Team, Audit |
| Customer | Profile, Notifications, Assistant |
| Merchant | Analytics, Disputes, Exceptions, Settings, Tasks, Team |
| Risk | Queue, Holds, Audit, Analytics, Reports, Transactions |
| Admin | Roles, Audit, AI, Evaluations, Integrations, Merchants, Observability, Policies, Security, Teams, Tenants |
| Auth | MFA, verify, forgot/reset password, workspaces |

## Non-goals

- Live payment provider credentials or real-money movement (Sarvam voice ≠ payment rails).
- Production IdP / real SMS email for MFA (sandbox can use DB-backed codes + loopback delivery log).
- Claiming assembled MVP release or pilot success from fixture module checks alone.
- Rewriting Mercury visual system or landing page.
- Merging multiple services into one monolith or shared root lockfile.
- Letting assistants/knowledge/voice mutate ledger, mint refunds, or bypass supervisor digests.
- A second `evaluation.v1` or `telemetry.v1` implementation that diverges from SN-016 / SN-015.

## Anti-goals

- Client-side “demo rows” or silent fixture fallback when `real-peers` is set.
- A second executor/ledger or editing SN-009 tables from other modules.
- Fake chat that pretends live model success without a persisted thread + explicit `evidence_mode` / model label.
- Cross-service SQL or deep imports across module boundaries.

## Constraints

- Follow root `AGENTS.md`: one accountable claim per GitHub issue/worktree; edit only owned roots; coordinate scope changes on issues before crossing ownership.
- Contract baseline: `sentinel.task-contracts.v1` / pinned SHA in module READMEs. New peers need versioned wire contracts + stubs for independence.
- Integer money, tenant/subject scope, fail-closed peers, unsampled financial audit unchanged.
- `NEXT_PUBLIC_*` stays public-only; session cookie is the portal bearer path via BFF.
- Each new service: `make check`, disposable Postgres in tests, README/CHANGELOG, preview port documented in sandbox matrix.
- Seed tools refuse non-sandbox / non `tenant-demo` (same spirit as simulator sandbox gate).

## Decisions (from conversation)

| Topic | Decision |
| --- | --- |
| Scope | **Everything** in the stub list + close the five shell limits |
| Data | **No mock UI data**; seed into DB; UI fetches via API only |
| Assistant / Knowledge / platform-ai / ops-activity | **New** HTTP+DB services under `services/` |
| Evaluations / Observability | **Most scalable:** extend SN-016 / SN-015 line — not duplicate contracts (see below) |
| Approvals UI | **Real** `packages/approval-ui` (SN-013); local substitute out of real-peers path |
| Voice | **On and wired** (SN-017); owner has Sarvam credits; secrets server-side only |
| Mode for product demo | **real-peers** + shared sandbox matrix tokens/ports |
| Money | Simulator only; SN-009 authority preserved |
| Delivery | Multi-wave program with parallel subagents per owned module after design + plan approval |

### Evaluations / Observability — locked architecture (builder-check #1)

**Evaluations:** `evals/core` (SN-016) stays the only `evaluation.v1` authority. Add Postgres-backed report store + HTTP serve/query inside that owned root (or a tightly coupled preview entry it owns). Portal Admin → Evaluations reads that HTTP API. CI/CLI keep using the same runner; durable portal reads share the same stored `RunReport` rows. Scalable because runners stay embeddable while the store/API can grow without a second contract.

**Observability:** `packages/telemetry` (SN-015) stays the SDK/redaction/`telemetry.v1` types. Add `services/observability` as HTTP+DB ingest/query for admin Observability pages, importing/using those types. Scalable because many services can emit via the package while one query service serves the portal; financial audit remains ledger-owned and unsampled.

### Approvals — locked (builder-check #3)

Supervisor approvals queue/detail must mount **real** `approval-ui.v1` from `packages/approval-ui`. Assembled real-peers path must not use the web local substitute. Decide still goes through case-api → ledger with exact digest; UI package does not gain money authority.

### Voice — locked (builder-check #2)

Wire `services/voice` + web slot; set `NEXT_PUBLIC_VOICE_ENABLED=true` (or equivalent) for the product demo. `SARVAM_API_KEY` / model ids in `services/voice` ignored `.env` only. Module checks stay credential-free via recorded fixtures. Text fallback remains if voice peer unavailable (fail visible, no silent fake transcript success presented as live).

## Builder defaults (my call unless overridden)

1. **Messages / Escalations / History / Audit (ops):** prefer extending **case-api** projections + events over inventing parallel case stores. Add DB tables/migrations only inside `apps/api` (or thin read models) when case-api already owns the case.
2. **Team (ops/merchant/admin):** prefer **identity** + **merchant-teams** before new team services.
3. **Notifications / Profile:** identity (+ optional notification table in identity or small `notifications` service if identity should stay auth-only).
4. **Exceptions / Tasks (merchant):** map to **merchant-inbox** / case-api operator queue semantics; do not invent a second case system.
5. **Settings (merchant):** merchant-scoped config table in an existing merchant service or small settings resource on merchant-teams — builder picks the thinner fit.
6. **Reports / Analytics (risk):** risk service aggregates from its DB + peers; no client-side charts from hard-coded arrays.
7. **Integrations / Policies / Security / Tenants (admin):** identity + config tables; policies remain versioned artifacts referenced by id, not edited into ledger rules from the UI without existing policy service flows.
8. **Ports (suggested):** assistant `8026`, knowledge `8028`, ops-activity `8029`, platform-ai `8030`, evals HTTP (evals/core preview) `8031`, observability `8033`, voice per existing voice README (document in matrix). Avoid collision with merchant-analytics `8032`. Update `integration/core/docs/sandbox-matrix.md` when preview lands.
9. **Seed:** one `make seed-sandbox` (or per-module `make seed`) writing matrix identities, cases, merchant metrics inputs, risk investigations, knowledge articles, assistant threads, eval reports, observability samples — all labeled synthetic.
10. **Web:** `NEXT_PUBLIC_SHELL_MODE=real-peers`, BFF proxies for every peer including approval-ui consumption path and voice, remove stub page components, delete fixture-only list UIs that invent rows (fail closed until seed/peer up).
11. **Voice budget:** live Sarvam only behind explicit env + sandbox; rate-limit and label `evidence_mode` accurately (recorded vs live).

## Architecture sketch

```
Browser (portal page)
  → apps/web BFF (/api/bff/<peer>/**) + httpOnly session
    → peer HTTP (real-peers)
      → peer Postgres (seeded)
Case/money path unchanged:
  web/case-api → workflow/evidence/policy → action-ledger → dispatcher → simulator → verifier
```

New peers are **read/write within their domain only**. Assistant may call read-only case/knowledge ports; it must not call ledger decide.

## Wave order

| Wave | Outcome |
| --- | --- |
| **0 — Foundation** | Shared sandbox compose/seed: Postgres schemas up, matrix tokens, web+api+identity+ledger+dispatcher+simulator+verifier+workflow+evidence+policy in real-peers; document ports/env |
| **1 — Merchant + Risk wire** | Analytics, disputes, settlements, refunds, team, exceptions/tasks; risk queue/holds/audit/analytics/reports/transactions — all from existing services + DB |
| **2 — Ops case surfaces** | Escalations, messages, history, audit, team via case-api/identity/merchant-teams |
| **3 — Identity / auth / customer** | Profile, notifications, workspaces, MFA/verify/forgot-reset as DB-backed sandbox flows |
| **4 — Intel + voice + approval-ui** | assistant, knowledge, ops-activity, platform-ai; evals/core HTTP+DB; services/observability; wire SN-013 approval-ui + SN-017 voice (Sarvam opt-in) |
| **5 — Admin remainder** | Roles, tenants, teams, policies, security, integrations, merchants, AI/evals/observability pages |
| **6 — Money-path E2E** | Assembly journeys green with DB state; real approval-ui; honesty labels; no fixture silent fallback |

Waves 1–2 can parallelize with early scaffolding of wave 4 services (empty schema + health) so portals do not stay on stubs longer than needed.

## Acceptance (program-level)

- No portal route in the stub inventory still renders “Not available yet” / “not connected to its service yet.”
- With peers down: pages show explicit error, not demo rows.
- With seed applied: each page shows at least one DB-backed record or an honest empty state from the API (`[]`), not hard-coded UI samples.
- `make -C <module> check` passes per touched module; root `make check` for metadata.
- Sandbox money journey runnable under simulator; financial audit only in ledger.
- README/changelog per owned module; contract hash recorded; evidence labels distinguish seed vs live-provider (live-provider unused).

## Evidence labels

| Dimension | This program |
| --- | --- |
| UI data | DB via real-peers |
| Seed | Synthetic sandbox (`tenant-demo`) |
| Payments | Simulator only |
| Assembled MVP claim | Only after wave 6 owner review — not implied by partial waves |

## What’s left to the builder

- Exact table DDLs, route shapes, and whether notifications live in identity vs a tiny new service.
- Whether ops-activity is a projection job from case-api outbox vs sync read-through.
- Assistant model: start with persisted threads + optional Sarvam/text model behind kill switch; never money authority.
- How evals/core exposes HTTP (in-module ASGI vs thin owned preview) without splitting contract ownership.
- GitHub issue/claim strategy and branch names per module.
- Precise OpenAPI/contract JSON for each new `*.v1` peer (assistant, knowledge, ops-activity, platform-ai, observability).

## Calls made (review while reading)

- Evaluations = extend `evals/core`; Observability = `packages/telemetry` + new `services/observability`.
- Real SN-013 approval-ui in real-peers; real SN-017 voice with Sarvam credentials local-only.
- Wave order 0→6 as above; parallel scaffolding allowed.

## Approval gate

Human must approve this full description before implementation or `writing-plans`. Reply **approve** (optionally with wave reorder notes) to proceed to the implementation plan.
