<a id="readme-top"></a>

<p align="center"><img src="media/readme/banner.png" alt="Sentinel: every refund, from complaint to confirmed credit" width="100%"></p>

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="apps/web/public/brand/sentinel-mark-inverse.svg">
  <img src="apps/web/public/brand/sentinel-mark.svg" alt="Sentinel" width="72">
</picture>

# Sentinel

**Investigate payment exceptions. Approve the exact action. Verify the credit.**

A payment operations workspace for customers, merchants and support teams, with human approval and deterministic controls around every refund.

[![Repository checks](https://img.shields.io/github/actions/workflow/status/Dijo-404/sentinel/repository.yml?branch=main&style=flat-square&label=repository)](https://github.com/Dijo-404/sentinel/actions/workflows/repository.yml)
[![License](https://img.shields.io/badge/license-Apache_2.0-555555?style=flat-square)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square)
![Node.js](https://img.shields.io/badge/Node.js-20%2B-339933?style=flat-square)

[Watch](#watch) · [See it](#see-it) · [Dev logins](#dev-logins) · [Quick start](#quick-start) · [How it works](#how-it-works) · [Verification](#verification) · [Documentation](#documentation)

</div>

> [!IMPORTANT]
> Sentinel is a development sandbox using synthetic payment data and a mock payment provider. A successful demo proves the tested simulator behavior; it does not move real money or establish production or pilot readiness.

## Watch

|                                     Sentinel in 90 seconds                                      |                                       How Sentinel works                                        |
| :---------------------------------------------------------------------------------------------: | :---------------------------------------------------------------------------------------------: |
| [![Sentinel in 90 seconds (1:29)](media/readme/poster-pitch.png)](https://youtu.be/U6B0VEkRMnc) | [![How Sentinel works (3:49)](media/readme/poster-explainer.png)](https://youtu.be/5mBIK9xCPPI) |

> Sandbox only. Every screen is the app running locally in fixture mode with synthetic data; payments go to a mock simulator. These recordings were captured against commit `1a64a55` on 15 November 2026. Follow the current setup instructions below for current behavior.

The posters open the videos on YouTube. Downloadable MP4 copies are hosted with the [sandbox demo media](https://github.com/Dijo-404/sentinel/releases/tag/readme-media-2026-11-15). The [README kit](media/README-kit.md) lists the assets and capture provenance.

## What Sentinel does

Sentinel helps investigate problems such as duplicate payments, captured payments that do not match an order, and refunds whose credit status is unclear. It brings the case, supporting evidence, proposed action, human decision and verified outcome into one workflow.

- **Customers** submit a payment issue and follow its progress.
- **Merchants** review payment operations, refund requests, settlement exceptions and disputes within their scope.
- **Operators** investigate cases, inspect evidence and escalate when needed.
- **Supervisors** approve or reject the exact proposed financial action.
- **Risk officers** review holds and risk decisions.
- **Platform admins** manage staff access and role assignments.

The model proposes an action. Authenticated identity, deterministic policy, supervisor approval and the action ledger decide whether it may execute. The verifier checks the outcome before the case can say the customer was credited.

## See it

|                     Case simulator                      |                                  Provider timeout                                  |                               Guardrails                                |
| :-----------------------------------------------------: | :--------------------------------------------------------------------------------: | :---------------------------------------------------------------------: |
| ![Case simulator](media/readme/demo-case-simulator.gif) | ![Provider timeout: reconcile, not resend](media/readme/demo-provider-timeout.gif) | ![Models propose, the server decides](media/readme/demo-guardrails.gif) |

These animated previews show the local fixture UI and simulated case behavior, captured at `1a64a55`. They do not demonstrate provider writes or customer credit on live rails.

## Dev logins

Open `/login` on your running dev deployment. For a local web server, use [localhost:3012/login](http://localhost:3012/login).

These accounts are seeded in the configured dev identity PostgreSQL database:

| Email                     | Password        | Workspace        |
| ------------------------- | --------------- | ---------------- |
| `customer@example.test`   | `demo-password` | Customer         |
| `merchant@example.test`   | `demo-password` | Merchant         |
| `operator@example.test`   | `demo-password` | Support Operator |
| `supervisor@example.test` | `demo-password` | Supervisor       |
| `risk@example.test`       | `demo-password` | Risk Officer     |
| `admin@example.test`      | `demo-password` | Platform Admin   |

**Sign-in behavior:** enter email and password; identity determines the workspace. One assignment opens its dashboard. Multiple assignments open a chooser containing only that account's workspaces. The login form does not let a user choose or grant a role.

**Sign-up behavior:** an unknown email opens `/signup` with the email prefilled. Customer and Merchant tabs support public registration; staff roles require admin invitation. Merchant references are generated by the server. `/customer/register` redirects to the Customer signup tab.

> [!NOTE]
> This table is for the seeded dev identity service. A fresh checkout needs the seed step below. The standalone web fixture uses its own test identities and passwords, defined in [the fixture stub](apps/web/tests/stubs/identity/index.ts).
>
> These are intentionally public, synthetic testing credentials. Keep them out of production and external pilots. Database passwords, session tokens and model keys remain private.

See the [credentials guide](deploy/dev/CREDENTIALS.md) and [identity README](services/identity/README.md) for seed roles and configuration.

## Quick start

### 1. Check the repository

The repository check needs Python 3.11+ and GNU Make. It does not require Docker, a database, model credentials or running services.

```bash
git clone https://github.com/Dijo-404/sentinel.git
cd sentinel
make check
```

This validates repository metadata, documentation links and repository tooling. It does not start Sentinel or test the assembled payment flow.

### 2. Install the tools for your module

| Work you want to do | Requirements                       | Start here                                                  |
| ------------------- | ---------------------------------- | ----------------------------------------------------------- |
| Python service      | Python 3.11+, `uv`, GNU Make       | The service's README and module-local `make check`          |
| Web application     | Node.js 20+, npm, GNU Make         | [Web setup](apps/web/README.md)                             |
| Stateful checks     | Docker for modules that require it | [Testing guide](docs/testing.md)                            |
| Full local sandbox  | Docker Compose v2 and the above    | [Sandbox runbook](integration/core/docs/sandbox-runbook.md) |

Each module owns its dependencies, lockfile and configuration. There is no root application manifest, shared lockfile or single root command that starts every service.

For example:

```bash
make -C services/action-ledger check
make -C apps/api check
make -C apps/web check
```

### 3. Seed a fresh local identity database

The local Compose file starts PostgreSQL and creates separate databases for the stateful peers. It does not start the application services.

```bash
docker compose -f integration/core/compose.yaml up -d --wait

export IDENTITY_MODE=real-peers
export IDENTITY_DEMO_PASSWORD=demo-password
export IDENTITY_DATABASE_URL=postgresql+psycopg://identity:identity@127.0.0.1:5432/identity

make -C services/identity seed
make -C services/identity preview
```

The connection string above belongs to the repository's local demo Compose setup. Use your own host-local database configuration on another deployment. The seed helper creates missing fixture accounts; it does not overwrite an existing account's password.

`IDENTITY_DATABASE_URL` enables PostgreSQL storage. Users and sessions then survive identity restarts. Fixture identity without that database setting uses process memory. Additional fixture principals are listed in the [identity README](services/identity/README.md).

### 4. Start the rest of the sandbox

Follow the [sandbox runbook](integration/core/docs/sandbox-runbook.md) for peer environment variables, migrations, service startup, workers and the web application. The identity command above runs only identity; the complete refund flow also needs the other peers.

Common local endpoints:

| Component         | Local address           |
| ----------------- | ----------------------- |
| Web               | `http://localhost:3012` |
| Case API          | `http://127.0.0.1:8080` |
| Identity          | `http://127.0.0.1:8012` |
| Workflow          | `http://127.0.0.1:8088` |
| Payment simulator | `http://127.0.0.1:8094` |

The runbook lists the remaining peers and ports. Public deployments need appropriate HTTPS, proxy trust and secret configuration; the local commands are not a production deployment recipe.

## How it works

### How a refund is authorized

![Six steps to authorize a refund](media/readme/flow-six-steps.png)

A duplicate-payment investigation follows this path:

1. **Intake:** the Case API records the customer's issue and a subject-bound order reference.
2. **Investigation:** workflow collects payment and order evidence, obtains a structured model proposal, and checks policy and risk.
3. **Approval:** the ledger records a proposal; a supervisor decides on its exact digest, case revision, policy version and expiry.
4. **Reservation:** the ledger validates fresh evidence and approval, then atomically reserves money and records the command and financial audit.
5. **Dispatch:** the dispatcher submits the refund using the ledger's stable `provider_ref`, including during retry or recovery.
6. **Verification:** the verifier reconciles provider events and separate credit evidence. Only the required postconditions permit verified case closure.

![The money path](media/readme/architecture.png)

```mermaid
flowchart TD
    UI[Customer and staff portals] --> API[Case API]
    API --> WF[Workflow]
    WF --> EV[Evidence]
    WF --> MODEL[Structured model proposal]
    MODEL --> WF
    WF --> POLICY[Policy and risk checks]
    WF --> LEDGER[Action ledger]
    SUPERVISOR[Authenticated supervisor] -->|Exact decision via Case API| LEDGER
    LEDGER -->|Reserved command| DISPATCHER[Dispatcher]
    DISPATCHER -->|Stable provider reference| SIM[Payment simulator]
    EV --> SIM
    SIM -->|Signed events| VERIFIER[Verifier]
    VERIFIER -->|Verified outcomes| LEDGER
    VERIFIER -->|Verified case result| API
```

### Financial authority

The **action ledger alone** owns authoritative approval, eligibility, reservation, action, outbox, lease and financial audit state. Workflow checkpoints, case revisions and merchant tools do not create a second ledger. The **dispatcher alone** writes to the payment provider.

Amounts use integer minor units with an explicit currency: `150000` INR minor units is ₹1,500. Approval and reservation remain bound to tenant, subject, original payment route, fresh evidence and the immutable proposed action.

| State                | What it means                                                               |
| -------------------- | --------------------------------------------------------------------------- |
| `PENDING`            | The refund is pending; this does not establish customer credit.             |
| `PROVIDER_CONFIRMED` | The provider confirmed the refund; separate credit proof is still required. |
| `CREDIT_CONFIRMED`   | The verifier accepted the required credit evidence.                         |
| `VERIFIED_RESOLVED`  | The case passed its configured authoritative resolution checks.             |

On timeout or crash, reconciliation keeps the original provider reference and reservation. An expired dispatch lease does not release reserved money. Escalation is a handoff, not financial resolution.

See [architecture](docs/architecture.md) and the [contract baseline](docs/independent-task-contracts.md) for interfaces, state ownership and failure rules.

## Proof

The images below record capture-time results, rather than current release acceptance.

![make -C integration/core check, fixture mode, 1a64a55](media/readme/proof-assembly-check.png)

The [original check transcript](media/video/proof/core-check-1a64a55.txt), recorded on 15 November 2026 at `1a64a55`, reports **129 passed, 1 skipped** and **18 passing report checks**. It explicitly states `mode: fixture`, `payment_provider: simulator` and `assembled_mvp_claimed: false`. Its `sn009_authority_exercised: true` field describes the fixture path; it is not evidence of assembled SN-009 financial authority.

![Paytm staging observations, captured and redacted](media/readme/proof-paytm-staging.png)

The Paytm image summarizes **nine redacted staging observations**. These are separately [recorded Paytm staging fixtures](integration/paytm-sandbox/README.md), not live payment or refund success: the shared test merchant returned errors for initiate and refund apply. The [capture claims manifest](media/video/CLAIMS.md) records sources and evidence labels for the videos.

## Verification

### What has been exercised

As of **15 November 2026**, separate sandbox checks have demonstrated:

- A full **API refund-to-credit flow** through real HTTP money peers and the simulator, using the live Sarvam model gateway: authenticated supervisor approval, ledger reservation, one provider refund side effect, signed events and credit-confirmed closure. Pending/provider-confirmed states kept the case open; duplicate credit delivery was idempotent. Details: [issue #144](https://github.com/Dijo-404/sentinel/issues/144).
- **Deployed browser authentication:** all six role logins, Customer/Merchant signup, unknown-email prefill, keyboard signup tabs and selection from an account's own workspaces. Details: [issue #154](https://github.com/Dijo-404/sentinel/issues/154).
- **Persistent dev identity:** the six accounts above and their sessions were verified after an identity restart using PostgreSQL. The persistence check was performed after the earlier browser run; it was a separate check. Details: [dev database verification](https://github.com/Dijo-404/sentinel/issues/154#issuecomment-6892679353).

These are scoped observations, not one continuous browser-to-credit certification. The payment provider remains synthetic; live payment rails, public TLS acceptance, strict release evidence and an external pilot remain separate work.

### What each check proves

| Check                 | Command or guide                                                                             | Evidence boundary                                                                                   |
| --------------------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Repository            | `make check`                                                                                 | Metadata, documentation links and repository-tool tests.                                            |
| Component             | `make -C <module> check`                                                                     | That module's behavior with its documented doubles and databases.                                   |
| Provider sandbox      | [Journey script](integration/core/scripts/run_sandbox_journeys.sh)                           | Simulator HTTP journeys and configured peer probes.                                                 |
| Ledger authority path | [Full-path runbook](integration/core/docs/sandbox-runbook.md)                                | The configured intake → approval → reservation → dispatch → verification path when its checks pass. |
| Release and pilot     | [Release kit](release/mvp/README.md), [pilot validation](validation/sandbox-pilot/README.md) | Only the evidence actually collected by those separate runs.                                        |

With a stack already running and configured, the journey script defaults to the provider-only path. Require the authority path explicitly when testing it:

```bash
SENTINEL_V1_AUTHORITY_PATH=1 SENTINEL_V1_REQUIRE_FULL_PATH=1 \
  ./integration/core/scripts/run_sandbox_journeys.sh
```

A passing fixture run or root metadata check cannot substitute for an assembled run. See [testing and evidence](docs/testing.md) for required failure, concurrency and financial acceptance checks.

## Configuration

- **Module-local configuration:** use each module's README and `.env.example`. The root [`.env.example`](.env.example) documents defaults; root checks do not load it.
- **Explicit modes:** `fixture` uses the documented doubles or local fixture state. `real-peers` connects configured peers and fails when required peers are unavailable, malformed or unauthorized. A real-peer simulator is still a simulator.
- **Persistent identity:** configure `IDENTITY_DATABASE_URL` and `IDENTITY_MODE=real-peers`. Limiters remain per process; shared limits are required before scaling identity replicas.
- **Trusted client addresses:** deployed web login requires explicit ingress authentication and `IDENTITY_TRUSTED_PROXIES`. Do not trust arbitrary forwarded headers. See [web configuration](apps/web/README.md) and [identity configuration](services/identity/README.md).
- **Provider event time:** set `SIMULATOR_CLOCK=system` for real-time sandbox events; the default fixed demo clock can fail verifier freshness checks.
- **Secrets:** keep database credentials, session tokens, model keys and webhook signing keys server-side. Never place them in `NEXT_PUBLIC_*` or commit host environment files.

The [configuration guide](docs/configuration.md) explains ownership and money controls. Demo bind opt-ins are described in the [dev credentials guide](deploy/dev/CREDENTIALS.md); default services refuse unsafe public demo binds.

## Repository layout

```text
apps/          Case API and Next.js web application
services/      Identity, workflow, evidence, policy, ledger, dispatcher,
               verifier, simulator, model gateway and optional operations services
packages/      Approval UI, contracts, persistence, telemetry and optional libraries
integration/   Core sandbox assembly and Paytm sandbox tooling
release/       Release evidence tooling
validation/    Sandbox and pilot validation tooling
evals/         Evaluation tooling and datasets
replay/        Replay tooling
benchmarks/    Benchmark tooling
tooling/       Workspace and lint tooling
scripts/       Repository validation scripts
tests/         Repository-tool regression tests
docs/          Architecture, contracts, task register and specifications
```

Optional voice, FinHarness, FinBench and merchant-operations modules have their own setup and evidence boundaries. They are not required to authorize or execute the core financial path. The [task register](docs/task-register.md) and [machine-readable task records](docs/tasks.json) define ownership.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md) and your module's instructions before editing. Coordinate work through the [GitHub Agents queue](https://github.com/Dijo-404/sentinel/issues?q=is%3Aissue%20is%3Aopen%20label%3Aagents), use the assigned branch and an independent worktree, and stay within the task's owned paths.

Useful repository commands:

```bash
make check       # Repository metadata and tool tests
make setup-lint  # Install the pinned lint tools
make lint        # Check Python and supported text/source formatting
make format      # Apply safe lint fixes and formatting
```

Run the affected module's `make check` as well. Keep contract changes compatible, document actual evidence modes and open a PR into `main` with its issue reference. The repository owner reviews and merges; agents do not push directly to `main` or enable auto-merge.

## Documentation

| Guide                                                             | Start here when you need to…                                                    |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [Sandbox runbook](integration/core/docs/sandbox-runbook.md)       | Bring up peers and run simulator or full authority journeys.                    |
| [Dev credentials](deploy/dev/CREDENTIALS.md)                      | Find synthetic login accounts and demo bind settings.                           |
| [Web application](apps/web/README.md)                             | Configure the portals, login, signup and BFF.                                   |
| [Identity service](services/identity/README.md)                   | Seed accounts, enable PostgreSQL and configure identity.                        |
| [Architecture](docs/architecture.md)                              | Understand boundaries, financial authority and runtime interfaces.              |
| [Repository structure](docs/repository-structure.md)              | Find the module that owns a component.                                          |
| [Testing](docs/testing.md)                                        | Understand what passing checks establish.                                       |
| [Configuration](docs/configuration.md)                            | Configure modes, secrets and persistence.                                       |
| [Task register](docs/task-register.md)                            | Find task scope, owners and GitHub issues.                                      |
| [Contract baseline](docs/independent-task-contracts.md)           | Check wire types, digests and compatibility rules.                              |
| [Paytm staging guide](docs/paytm-testdata-integration.md)         | Understand the separately configured Paytm sandbox tooling.                     |
| [GitHub workflow](docs/github-workflow.md)                        | Follow claims, labels, review and handoff rules.                                |
| [Phase 1](docs/sentinel-p1.md) and [Phase 2](docs/sentinel-p2.md) | Read planned product intent; these specifications are not implementation proof. |
| [Pitch deck](docs/Sentinel_Pitch_Deck.pdf)                        | Review the project narrative.                                                   |
| [Changelog](CHANGELOG.md)                                         | Read coordinated repository-level changes.                                      |

## License

[Apache License 2.0](LICENSE).

<div align="center">
  <sub>Built by <a href="https://github.com/Dijo-404">Dijo-404</a> · <a href="#readme-top">Back to top</a></sub>
</div>
