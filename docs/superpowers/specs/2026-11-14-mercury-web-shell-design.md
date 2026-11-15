# Sentinel web shell — Mercury landing + portals

**Date:** 2026-11-14  
**Owned root:** `apps/web/`  
**Status:** approved 2026-11-14 — human: proceed with subagents

## Intent

Replace the current plain portal-picker and scaffold chrome in `apps/web` with a premium Mercury-inspired product surface: a marketing landing page, a simple shared login, and rich role dashboards. First dashboards to carry real visualization are **merchant**, **operator**, and **supervisor**, built in parallel after this design is approved.

Why now: the shell already has six role trees, fixture auth, BFF, and approval paths, but the UI is a graphite scaffold. Product feel should match payment-ops trust (quiet bank / precise software) while making queue, approval, and merchant data scannable.

## Goals

1. `/` is a night-world marketing landing (Mercury tokens + Ramos/Cometly/Wezom motion and viz energy).
2. Nav **Log in** opens one shared login; credentials + server role decide the destination.
3. After login, each role lands in a light-world dashboard framed by a night sidebar/shell, with existing `PORTAL_NAV` menus.
4. Merchant, operator, and supervisor dashboards get rich, labeled fixture/simulator visualizations in the same visual system.
5. Keep auth, BFF, case-api ports, approval digest binding, and `make -C apps/web check` green.
6. Framer Motion for UI motion; lightweight 3D/canvas hero on landing only; charts for data usefulness.

## Non-goals

- Assembled product / live payment / pilot claims.
- Changing SN-009 ledger, dispatcher, or identity service code outside `apps/web`.
- Replacing `approval-ui.v1` peer package (local substitute stays until assembly).
- Building customer / risk / admin rich viz in this pass (shell restyle only).
- Real analytics peer wiring beyond existing case-api reads + local fixture aggregates.
- Dark-mode toggle; night/day is page-role based (landing night, app light + night chrome).

## Anti-goals

- A second ledger, editable refund amounts, or client-minted digests.
- Silent fixture fallback in `real-peers` mode.
- Multiple solid primary buttons competing in one CTA group.
- Heavy bold type, hard outlined buttons, or status greens/oranges in chrome (status colors only inside data viz and status chips).
- Claiming live metrics when data is fixture/simulator.

## Constraints

- Work only in `apps/web/` (manifest, lockfile, code, tests, README, changelog).
- Branch/worktree per module AGENTS (`feat/sn-012-ui-shell` or recorded alternative).
- Contract hash and ports unchanged unless a versioned adapter is explicitly required (not in this design).
- Preserve `data-testid`s used by existing browser tests where possible; update tests when chrome changes.
- No secrets in `NEXT_PUBLIC_*`.
- Accessibility: visible focus, keyboard nav, `prefers-reduced-motion`, contrast ≥ 4.5:1 on text.
- Touch targets ≥ 44px on interactive pills.

## Decisions (from conversation)

| Topic         | Decision                                                                                                                                                   |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Surface       | Rebuild inside existing `apps/web`, replace old UI                                                                                                         |
| Flow          | Landing → Log in → role dashboard + menus                                                                                                                  |
| Login         | **One shared `/login`**. Server owns role. Legacy `/{role}/login` redirect to `/login` (optional `?portal=` for copy only).                                |
| Viz priority  | Merchant + operator + supervisor in parallel after approval                                                                                                |
| Visual system | Mercury tokens (night/canvas/indigo/lavender, light type weights); Inter as Arcadia substitute                                                             |
| References    | Ramos (bento + KPI widgets), Cometly (night hero → day product viz), Wezom (product stage / multi-panel), Ventriloc (pill nav, dashboard mock as hero art) |
| Motion        | Framer Motion; respect reduced motion                                                                                                                      |
| 3D            | Landing hero atmosphere only (CSS/canvas/Three lightweight); not required inside every dashboard cell                                                      |

## Information architecture

```
/                          night landing (public)
/login                     shared login (public)
/{role}/login              redirect → /login
/{role}/dashboard          protected light dashboard
/{role}/*                  existing protected routes, new shell
/ops, /intake, …           keep; restyle shell only
```

Post-login redirect: `safePortalRedirect` / existing `portalPath(role)` → `/{role}/dashboard`.

Landing secondary CTAs (builder call): **Open demo** scrolls to product viz or opens fixture login hint; **Contact** can be a non-functional mailto or in-page anchor — not a second money path.

## Visual system (tokens)

Implement as CSS variables in `apps/web` (names match Mercury kit):

**Surfaces:** `night` `#171721`, `night-raised` `#1e1e2a`, `canvas` `#fbfcfd`, `surface` `#ffffff`, `lavender` `#edecfb`, `surface-tint` `#fbfbff`  
**Accent:** `primary` `#5266eb`, `on-primary` `#ffffff`, `periwinkle` `#9cb4e8`  
**Text:** `ink` `#28253b`, `ink-secondary` `#554e7b`, `on-dark` `#ededf3`, `fog` `#c3c3cc`  
**Type:** Inter variable, weights 360–480 (cap 500 for eyebrows). Hierarchy by size, not bold.  
**Radius:** cards `12px`, primary pill `32px`, secondary pills `40px`.  
**Elevation:** tonal fills first; hairline shadow only under pricing-like or floating mock panels.  
**Spacing:** 8px base; section gaps 80–128px on landing.

Status chip colors stay domain-mapped (existing status system) and appear only on data rows/chips, not as page chrome accents.

## Landing page

**Pattern:** Real-time / ops landing + trust (ui-ux-pro-max): hero with live-feeling product preview → stats → solution bento → quote → closing CTA → night footer.

**Chrome:** 72px night nav — wordmark left, links center (Features, How it works, Roles), Log in (glass) + primary **Open account** / **Get started** right. Footer night multi-column.

**Hero:** centered display headline (payment ops: investigate → approve → dispatch → verify), short lead, email-capture-style or dual CTAs (one solid indigo). Right or below: interactive product stage (tilted dashboard panels / soft 3D) showing synthetic queue + approval metrics. Label “Simulator preview”.

**Sections:** logo strip (monochrome), four stat blocks, feature cards on `night-raised`, light-world feature strip optional, centered quote, closing CTA band.

**Motion:** one orchestrated load sequence; scroll reveals sparingly; pause/stop any auto-rotating logos; static under reduced motion.

## Shared login

- Route `/login` restyles `RoleLogin` into a single form without forcing a role picker when possible.
- **Builder call:** keep hidden `role` optional. If email matches one fixture assignment, activate that role (existing identity behavior). If multiple workspaces, show authorized workspace links after attempt (already in `RoleLogin`). For demo clarity, allow a compact “Workspace” select of the six portals that only sets the expected-role hint for `loginAction` — not a grant.
- Preserve fixture banner and demo credential discoverability (footer note or collapsed “Demo users”).
- Customer register stays at `/customer/register`; link from login when workspace=customer.

## App shell (all protected portals)

Replace top-only `ProtectedShell` with:

- Night left sidebar (desktop) / drawer (mobile): wordmark, role label, nav from `PORTAL_NAV`, sign out.
- Canvas main: page content.
- Active nav indicator uses `primary`.
- Fixture/real mode banner remains visible when applicable.
- Keep `data-portal={role}` and logout `data-testid="logout"`.

Customer / risk / admin get the new shell and light restyle of existing pages; rich viz widgets are out of scope this pass.

## Dashboard specs (parallel build)

Shared building blocks (one design system module):

- `StatBlock`, `FeatureCard` (light/dark), `TrendPill`, `ChartCard`, `QueueTable`, `Empty/Loading/Error` states
- Chart library: Recharts (or equivalent lightweight React charts) — fixture series only unless case-api already returns the field
- Every metric panel: `role="status"` or caption “Simulator / fixture — not live production metrics”

### Merchant overview (`/merchant/dashboard`)

**Job:** see money-adjacent ops health without ledger authority.

**Widgets (fixture aggregates + any scoped reads later):**

1. KPI row: captured volume (display), open exceptions, pending refund _requests_, settlement status summary — all synthetic unless peer exists
2. Area/line: volume vs refunds over time (fixture series)
3. Table: recent exceptions / transactions stub with masked refs
4. Nav unchanged: Dashboard, Transactions, Settlements, Refunds

**Hard line:** refund UI remains request/advisory; no approve/execute; no second reservation.

### Operator queue (`/operator/dashboard` + wire `/operator/queue`)

**Job:** triage cases.

**Widgets:**

1. KPI row: open, waiting, overdue (client-derived or fixture), interventions
2. Status histogram / donut from `listOpsCases()` when available; else fixture
3. Wire `/operator/queue` to existing `OperatorQueue` + `CaseClient` (same as `/ops`)
4. Dashboard embeds summary + link into full queue

**Hard line:** no approval controls; evidence paths stay `enableApproval` off.

### Supervisor approvals (`/supervisor/dashboard` + `/supervisor/approvals`)

**Job:** decide on exact digest-bound proposals.

**Widgets:**

1. KPI row: waiting approval count (from `listOpsCases({ status: "WAITING_APPROVAL" })`), oldest age if timestamps exist else omit
2. Pipeline strip of case/action states (visualize enums only)
3. Keep approvals table → decision workspace; enrich display-only (amount from evidence, masked txn)
4. Decision path unchanged: exact `DecisionRequest` fields; tests in `supervisor-approvals.test.tsx` stay authoritative

**Hard line:** no amount edits; no client-minted digest; approval ≠ credit.

## Technical approach

1. Add deps in `apps/web/package.json` only: `framer-motion`, chart lib, optional `@react-three/fiber`/`three` if hero 3D stays small; prefer CSS/canvas if bundle cost is high (**builder call:** start CSS + Framer + Recharts; add Three only if hero needs it after first pass).
2. Token CSS + typography in `globals.css` / layout fonts.
3. New components under `src/components/marketing/`, `src/components/shell/`, `src/components/viz/`.
4. Parallel implementation tracks after plan approval:
   - Track A: landing + tokens + shared shell + `/login`
   - Track B: merchant dashboard viz
   - Track C: operator dashboard + queue wire-up
   - Track D: supervisor dashboard + approvals chrome (not decide logic rewrite)
5. Update browser tests for new home/login; keep auth and approval contract tests green.
6. Changelog + README routes/screenshots commands.

## Out of scope for builders unless design amended

- New identity or case-api endpoints
- MFA / invite flow redesign beyond visual restyle
- Pricing page, marketing CMS
- Mobile native apps

## Success criteria

- Human can open `/`, understand Sentinel in one viewport, click Log in, sign in with fixture user, and use sidebar menus on merchant/operator/supervisor with useful charts/tables.
- `make -C apps/web check` passes.
- Fixture vs real-peer labeling correct; real-peer errors visible.
- Reduced-motion path does not rely on motion to convey meaning.

## Builder calls (defaults)

1. Workspace hint select on `/login` for demos; identity still authorizes.
2. Charts: Recharts; hero 3D deferred unless CSS stage feels flat.
3. Primary landing CTA label: **Get started** → `/login`. Secondary nav **Log in** → `/login`. No “Open account” (not a bank signup product). Customer register remains `/customer/register` only.
4. Signed-in visit to `/`: stay on marketing landing; nav swaps Log in for **Dashboard** → `/{role}/dashboard`. No forced redirect.
5. Customer / risk / admin and non-dashboard pages: new shell + token cascade only (no rich viz this pass).
6. Parallel tracks: Track A (landing + tokens + shell + `/login`) first, then B/C/D dashboards in parallel.
   )
