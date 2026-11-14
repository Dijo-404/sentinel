# SN-012 / SN-038 changelog

## Unreleased

### Fixed — 15 November 2026 (portal peer wiring + fixture hardening, Refs #129)

- Fixture portals bind case-stub `decide` to the active assignment via `PortalCaseShell` (not `NEXT_PUBLIC_DEMO_ROLE`).
- Merchant real-peers withholds metrics when assignment has no `merchant_ref` (no silent fixture identity).
- Case stub: supervisor-only `decide`; trim/reject blank `order_reference`; unique create ids with in-memory case/event store so messages and escalations show on the timeline.
- Identity stub: invite rejects emails that already belong to an ACTIVE user (`DUPLICATE`).
- Dual-role users switch workspace in-session via `selectAssignment` (sidebar + unauthorized), no sign-out.
- Customer Cases lists via `GET /v1/customer/cases`; Transactions stay fixture-labeled / real-peers unavailable (no list peer).
- Merchant metrics + risk dashboard BFFs (`MERCHANT_ANALYTICS_BASE_URL`, `RISK_BASE_URL`); settlements findings via settlement BFF; merchant tx/refunds fixture or unavailable.
- Ops labels: "Waiting approval" = cases in `WAITING_APPROVAL`; "Pending approvals" = ledger-owned proposals (may stay 0 until ledger count is projected).

### Fixed — 15 November 2026 (dashboard QA pass, fixture mode, all seven demo logins)

- Spacing: `.stack`/`.row` children drop UA block margins (grid/flex gaps no longer add ~50px under headings); panels and slot boxes trim first/last child margins. Timeline list keeps panel padding.
- Ops dashboard: operator status chart is a bar chart (statuses overlap, so a donut total misread the open count); both charts share readable horizontal axis labels and the Sentinel tooltip. Queue status/link moved out of the KPI grid.
- Decision workspace: operators see the proposal read-only with a "Supervisor decision required" notice; Approve/Reject render only for an active supervisor assignment (resolved server-side). Server still enforces.
- Customer Report page hosts the intake form inside the portal shell; "Legacy intake" removed from customer nav (route kept).
- Intake: trims message and order reference, blocks a blank order reference, clears the message after a case is accepted, shows language names; customer-facing copy.
- Operator queue "Open evidence" stays in the portal (`/operator/cases/[caseId]/evidence`); case IDs URL-encoded.
- Timeline shows local timestamps and plain polling copy.
- Registration failures (existing email or invalid input) share one sign-up message, so the reply no longer reveals registered emails (previously a distinct sign-in failure text); name field autocompletes.
- 40 placeholder pages show user-facing "not connected yet" copy instead of developer scaffold text.
- Mobile: KPI cards two-up at 390px; staff tables scroll inside their panel instead of widening the page; intake fields keep a gap when stacked; fixture banner wraps cleanly.

### Changed — 14 November 2026 (ops shared workspace)

- Operator and supervisor portals share one nav (queue, approvals, escalations, messages, assistant, knowledge, activity, history, team, audit). Layouts accept either active assignment via `requireAnyRole`.
- Both dashboards render `OpsCombinedOverview`: parallel operator + supervisor projections; one peer failure leaves the other section visible.

### Changed — 14 November 2026 (premium UI)

- WebGL: adds `three@0.186.1`, `@react-three/fiber@9.8.1` and `@types/three@0.186.0` (exact pins). Scenes load with `next/dynamic` (`ssr: false`), pause when off-screen, and fall back without WebGL (`useWebGL`).
- Landing rebuilt on the Mercury tokens: centred word-reveal headline over a WebGL horizon planet (fresnel rim, four stage orbits with case lights, starfield, pointer parallax) driven by stage chips; a simulated merchant dashboard that straightens on scroll; count-up facts; analytics with WebGL 3D bars, SLA gauge and 30-day trend; a scroll-pinned four-stage walkthrough; guardrails; role switcher with live tiles; and a pointer-lit footer wordmark. Framer Motion throughout under `MotionConfig reducedMotion="user"`.
- Brand mark: the owner-supplied cube logo redrawn as vector `public/brand/sentinel-mark.svg` plus a light-on-dark `sentinel-mark-inverse.svg`; used by `LogoMark` in the landing nav, footer and sidebar, by `.brand::before` on auth and legacy pages, and as the favicon.
- Site-wide custom arrow cursor (`components/cursor.tsx`, mounted in the root layout) for fine pointers only; text fields keep the I-beam and touch devices keep the native cursor. While a select picker, modal or popover is open (browser top layer, above any z-index) the native pointer takes over so the cursor never hides behind it.
- New viz primitives in `components/viz`: `Sparkline`, `Donut` (interactive legend), `Heatmap`, `RadialGauge`, `PipelineFunnel`, `Bars3D` (WebGL bars with a projected value label per bar and focusable axis buttons; flat fallback), `AreaTrend` (`yFormat`), `ChartTooltip`, `Legend`, `format.ts` (`usdCompact`). `fixtureSeries.dateLabels` gives fixed calendar axis labels. `StatBlock` takes optional `series`/`trend`; `TrendPill` colours by meaning (`tone`); `ChartCard` takes `subtitle`, `aside`, `testId`.
- Data display: fixture volume charts are in dollars per day and sum to the KPI they sit beside; axes show dates and compact currency.
- Dashboards rebuilt with `DashboardHeader`: merchant (KPI sparklines, area trend, reasons donut, 3D weekday bars, arrival heatmap, exceptions table), operator (status donut, work-the-queue steps; sparklines only in fixture mode), supervisor (pipeline funnel, grouped donut), and customer/risk/admin `PortalDashboard` with fixture KPIs, trend and gauge. Fixture banner and real-peer error paths unchanged.
- Sidebar: stroke icons per nav item, animated active pill; brand, nav and account share one inset; the account (email only) sits at the bottom above Sign out for every workspace.
- Forms: every single-line input and select is 44px tall with a custom chevron inset to the text padding. Where `appearance: base-select` is supported, selects open a styled, animated picker (rounded panel, hover tint, checkmark on the chosen option, chevron flips when open) in light and night variants; other browsers keep the native popup. Short portal pages no longer stretch grid rows to the viewport height.
- Evidence: `make -C apps/web check` 13 files / 81 tests passed; `next build` passed; root `make check` passed with `apps/web/node_modules` and `.next` moved aside (the root validator scans installed package READMEs). Fixture mode only; visual check in Chromium at 1440px and 375px.

### Changed — 14 November 2026

- Mercury shell rebuild: night marketing landing at `/`, shared `/login` with workspace select, role `/<role>/login` redirects to `/login?portal=…`, night `AppSidebar`/`ProtectedShell` for all portals, and rich fixture viz on merchant/operator/supervisor dashboards (Refs SN-012).

### Fixed — 14 November 2026

- Operator and supervisor overviews prefer `CaseClient.getOperatorDashboard` / `getSupervisorDashboard` aggregates; PeerError or missing port shows explicit unavailable — never page-scoped `listOpsCases` or fake KPIs.
- Supervisor decision workspace loads authoritative `ActionRecord` via `getAction` (ledger BFF `/api/bff/ledger` → `GET /v1/actions/{id}`); real-peers fail closed without silent `demoAction` digests. Decision expiry from evidence freshness (fixture keeps labeled `FIXTURE_DECISION_EXPIRES_AT`).
- Case timeline polls `listEvents` and wires message/escalate controls; operator queue paginates on `next_cursor` and links timeline to `/operator/cases/{id}` (not customer `/cases`).
- Merchant and role portal dashboards withhold fake KPIs; customer uses scoped case-api dashboard when available, otherwise explicit unavailable.
- Portal BFF `/api/bff/case/**` requires `sentinel_session` only; removed `CASE_API_BEARER_TOKEN` fallback so unauthenticated browser callers cannot borrow the service token (401, no upstream call).
- Portal case-api calls use per-request `sentinel_session` via BFF `/api/bff/case/**` (and `getServerCaseClient`); ShellProvider no longer embeds process-wide `CASE_API_BEARER_TOKEN`. Service token remains optional server fallback only.
- `requireRole` / `checkRole` / `requireAnyRole` enforce active `assignment.role` only (dual-role mismatch covered in tests).
- Supervisor decision workspace loads action id from queue/case + refund evidence; removed `demoAction.action_id` hard-gate.
- `/auth/accept-invitation` wires identity accept-invitation and sets session cookie on success.
- Login fails closed when `selectAssignment` returns null (no cookie). Cookie `maxAge` aligned with session `expires_at` (~12h).
- `mapMe` prefers peer `expires_at` when present.

### Added — 14 November 2026

- Supervisor approvals queue + decision workspace (`/supervisor/approvals`, `/supervisor/approvals/[actionId]`) embed local `approval-ui.v1` substitute with exact digest/revision/expiry via case-api `decide` proxy (Refs #100 / M4.2).
- Supervisor case review `/supervisor/cases/[caseId]` with opt-in approval slot; legacy `/ops` evidence keeps approve controls off (`enableApproval` default false).
- Real-peers identity.v1 HTTP client (`createRealPeerIdentityClient`): login/register/me/workspaces select/logout + admin invite/list against `IDENTITY_BASE_URL` (default `http://127.0.0.1:8012`). Fail-closed on missing base URL, network failure, or malformed peer JSON; fixture stub retained for `NEXT_PUBLIC_SHELL_MODE=fixture`. Session token stays in httpOnly cookie — never `NEXT_PUBLIC_*` (Refs #100).

### Fixed — 14 November 2026

- Session cookie set only after portal role match; mismatch clears cookie and revokes provisional session. Active assignment bound to requested portal before cookie write (Refs #100 / PR #107).
- `registerCustomerAccount` rejects privileged client fields before identity peer call. Safe redirects normalize path, reject `..`, require exact `/{role}` prefix.
- Legacy `/intake` and `/ops` gated with `requireRole` / `requireAnyRole` (customer; operator|supervisor).

### Added — 14 November 2026

- SN-038 six role portals: `/customer|merchant|operator|supervisor|risk|admin` login + protected dashboards; customer `/register`; shared `RoleLogin`, `ProtectedShell`, unauthorized workspace chooser (Refs #100).
- Admin users directory + invite form wired to `tests/stubs/identity`; `PermissionPreview` advisory only; staff invite rejects `customer` role.
- Server session cookie helpers (`sentinel_session`), fixture identity double, real-peers refuses `NEXT_PUBLIC_*` identity bearers.
- Design tokens: graphite/white surfaces with blue primary (§13.1). Legacy `/intake` and `/ops` kept for compatibility.
- Vitest coverage for identity stub, auth helpers, role-mismatch UI, and no customer staff-register path.

### Fixed — 14 November 2026

- `loadShellConfig` refuses `real-peers` when bearer would come from `NEXT_PUBLIC_DEMO_TOKEN` alone without `CASE_API_BASE_URL`. Portal shell never embeds `CASE_API_BEARER_TOKEN`. `.env.example` warns never put secrets in `NEXT_PUBLIC_*`.

### Added — 14 November 2026

- `GET /v1/capabilities` assembly probe: `{ contract_version, component: "web-shell", port: "web-shell.v1", mode }` from `NEXT_PUBLIC_SHELL_MODE` (Refs #76).

### Changed — 14 November 2026

- `.env.example` uses canonical sandbox tokens/ports (`tok-customer`, case API `:8080`, web `:3012`). Refs #77.

### Added — 13 November 2026

- Next.js web shell (`web-shell.v1`): text intake, case timeline, operator queue, evidence workspace.
- Domain masking for subject/transaction/provider/order refs; exact pending/provider/credit/escalation labels.
- Local stubs for `case-api.v1`, `approval-ui.v1`, `voice.v1` under `tests/stubs/` (valid, unavailable, malformed, unauthorized_or_out_of_scope).
- Real-peer case-api adapter that surfaces failures without fixture fallback.
- Approval and voice component slots with local substitutes; voice disabled by default.
- Module `Makefile` (`make check`), `.env.example`, contract snapshots/fixtures, Vitest browser-state checks.

### Implementation status

- Standalone fixture checks implemented. Assembled SN-007/SN-013/SN-017 real-peer evidence unverified.
- Contract baseline SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
