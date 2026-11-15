# Deployed six-role Playwright review — 15 November 2026

Issue: [#168](https://github.com/Dijo-404/sentinel/issues/168).
Branch: `fix/role-user-journeys`.
Target: `http://65.2.68.199/`, the synthetic development sandbox.
Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Scope and evidence

Normal Chromium sessions used the six documented demo accounts. No secure-origin
bypass, mocked browser responses, production data or real payment rails were used.
Desktop viewport: 1440 × 1000. Mobile viewport: 390 × 844.

The navigation run exercised **62 role/page combinations**, taking desktop and
mobile screenshots. Shared operations pages were exercised separately with both
operator and supervisor identities. It also checked 19 denied cross-role portal
visits, login persistence after reload, sign-out, protected access after sign-out,
keyboard command palette, saved theme, and mobile navigation for every role.

| Role           | Page combinations | Observed supported flows                                                                                                                                               |
| -------------- | ----------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Customer       |                 7 | Login/reload, transaction catalog, invalid/scoped intake, accepted-case navigation, cases, profile validation/save/reload, notifications, assistant                    |
| Merchant       |                10 | Login/reload, dashboard, transactions, settlements, refund catalog, disputes, exceptions, analytics, team and settings; Tasks remains explicitly unavailable           |
| Operator       |                11 | Active-role metrics, queue/filter/replay, case/evidence, message submission, assistant, knowledge search, messages, activity, escalation/history/audit lists           |
| Supervisor     |                13 | Active-role metrics, shared operations pages, pending proposal, exact rejection, read-only recorded decision after full reload, team                                   |
| Risk Officer   |                 7 | Dashboard, investigations, restrictions, findings, transactions, analytics, reports                                                                                    |
| Platform Admin |                14 | Security projections, users, invalid/valid invitation, roles, tenants, teams, merchant catalog, policies, AI metadata, integrations, evaluations, observability, audit |

Additional browser validation covered empty login, wrong password, unknown-email
signup prefill, invalid email, short password, missing business name, duplicate
signup, blank profile name, missing reset fields, invalid reset code, and invalid
invitation. Rejected login/signup/invitation forms retain typed identity details.
Passwords and signup consent can require re-entry after a rejected submission.

A new synthetic customer initially saw the seeded customer's case counts. After
the API fix, another new customer saw zero open and zero resolved cases. A seeded
customer's calls to policy, operations activity and risk APIs initially returned
200 through shared peer credentials; after the proxy fix they returned 401/403.
A direct operator proposal visit exposed no decision controls. Supervisor rejection
was recorded by the real HTTP case/ledger peers; reloading that action now retains
the rejection and hides decision buttons.

## Confirmed fixes

| Failure                                                                         | Cause and correction                                                                                                                                                                                                                  |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Login appeared successful but requests returned 401; reload signed the user out | HTTP Chromium rejected the production Secure cookie. Non-Secure cookies now require both explicit sandbox flags; default production remains Secure.                                                                                   |
| Fresh customer inherited another customer's case counts                         | Case API assigned `subject-demo-42` to every customer. Removed the default; legacy grants require exact server-configured tenant/user bindings.                                                                                       |
| Any logged-in account could use privileged shared peer credentials              | BFF checked cookie presence only. Credential substitution now requires live identity validation, an allowed role, sandbox mode, and exact user/tenant/role/merchant binding. Admin gate projections separately verify admin identity. |
| Operator/supervisor dashboards requested forbidden metrics                      | Fetch and render only the active assignment's projection. Shared layouts now keep that assignment's role and navigation; operator case review has no supervisor controls.                                                             |
| Denied page offered no way back for a single-workspace account                  | Full workspace lists include the current authorized assignment. Compact sidebar lists still omit it.                                                                                                                                  |
| Implemented pages were missing from normal navigation                           | Added the implemented customer, merchant, risk and admin destinations; supervisor Team is omitted from operator navigation.                                                                                                           |
| Mobile tables, metrics and timestamps expanded the page                         | Grid children can shrink, tables have bounded scroll regions, long values wrap, and merchant KPI cards allow useful reading width. Table content retains readable column widths.                                                      |
| Admin AI/evaluations/observability returned 503                                 | Started the existing services with isolated PostgreSQL databases and synthetic metadata seeds; configured private upstream credentials.                                                                                               |
| Merchant settings returned 404                                                  | The deployed Teams service had no database/settings row. Configured its own database and ran its idempotent synthetic seed.                                                                                                           |
| Merchant disputes returned 403                                                  | Configured an exact demo merchant credential and allowed scoped merchant listing. All detail and mutation operations retain operator/supervisor authorization.                                                                        |
| Validation erased typed identity details                                        | Preserve login email, signup name/email/business name, and invitation name/email/tenant/reason in client state.                                                                                                                       |
| Accepted intake exposed only a raw ID                                           | Added a direct View case link using the accepted server ID.                                                                                                                                                                           |
| Rejected/approved action could not reopen after leaving the pending queue       | Load its authoritative action first, then its case and evidence. Existing approval records remain read-only after refresh. Rejection copy does not imply execution.                                                                   |

## Commands and artifacts

```sh
make -C apps/web check
# TypeScript + 57 files / 351 tests passed.
make -C apps/api check
# Ruff + 90 tests passed, including disposable PostgreSQL checks.
make -C services/merchant-disputes check
# Ruff + 26 tests passed, including disposable PostgreSQL checks.
make check
# Repository metadata/docs validation + 21 tests passed.

uv run --with playwright playwright install chromium
uv run --with playwright python apps/web/scripts/role-journeys.py \
  --base-url http://65.2.68.199 --output-dir /tmp/sentinel-role-journeys
```

The actual run used `/tmp/sentinel-role-qa-env/bin/python` with installed
Playwright 1.65.2 and Chrome for Testing 158.0.8127.18 at
`/home/dj/.cache/ms-playwright/chromium-1254/chrome-linux64/chrome`, supplied through
`--browser-executable`. The runner's JSON report distinguishes expected Tasks
unavailability from unexpected alerts, HTTP failures, crashes and viewport overflow.

Local session artifacts are under `/tmp/sentinel-role-qa/`: per-role JSON,
screenshots, `workflow-results.json`, validation results, before/after API boundary
probes, and recorded-decision reload proof. Session credentials were not persisted
in these artifacts. Screenshots and raw logs are local review evidence, not checked
into the repository. The final navigation artifact directory is `/tmp/sentinel-role-qa/final5`.
The compact [results record](role-user-journeys-results.json) is checked in.

The optimized Next production builds passed on the deployment host. Final build
location: `/opt/sentinel/.role-qa-5/apps/web`. Only `sentinel-web.service` has a
working-directory override selecting it. Previous web builds remain available.
The API and dispute module changes have separate source backups under
`/opt/sentinel/.sandbox-history/role-qa-api` and `role-qa-disputes`.

Rollback of web only: remove or change
`/etc/systemd/system/sentinel-web.service.d/role-qa.conf`, run
`systemctl daemon-reload`, and restart `sentinel-web`. The original source/build
at `/opt/sentinel/apps/web` was preserved. Returning to the original build also
returns its HTTP cookie defect. Host-local environment files and credentials
remain private. No main push, merge or auto-merge occurred.

## Limits

- The payment provider is a simulator. No new approval-to-dispatch-to-credit
  certification is claimed. This review exercised a supervisor rejection; approval
  and credit safety still have separate component/previous assembly evidence.
- Frontend `real-peers` means real HTTP adapters. Several older auxiliary peers
  still run their existing fixture modes or use synthetic data. The three newly
  started admin peers use separate PostgreSQL stores and explicitly synthetic
  seeds. No live provider or production telemetry evidence is implied.
- `/merchant/tasks` is an intentional existing capability gap: merchant-sla is not
  wired into that page. The unavailable state remains visible and the page is not
  advertised in navigation. No fake task rows were added.
- Newly registered merchants can sign in and retain their generated merchant scope,
  but their operational peers still need per-merchant provisioning. They do not
  inherit the demo merchant's credential or records. This is not complete merchant
  onboarding acceptance.
- Risk list pages expose read models; this review does not certify risk hold-write
  workflows. Staff invitation delivery is the sandbox identity flow, not proof of
  external email delivery. Chromium desktop/mobile viewport checks do not establish
  Safari, Firefox, screen-reader or physical-device acceptance.
- Root checks validate repository metadata. Standalone tests use component doubles
  and disposable databases. Neither those checks nor this sandbox audit establishes
  product release or external pilot readiness.
