# Repository structure and ownership

## Root responsibilities

| Path | Responsibility |
| --- | --- |
| `AGENTS.md`, `CONTRIBUTING.md` | Shared rules, claims, branches, review and handoff |
| `README.md`, `CHANGELOG.md` | Honest project entry point and coordinated release/repository changes |
| `.editorconfig`, `.gitattributes`, `.gitignore` | Portable formatting, binary handling, ignored secrets/build output/worktrees |
| `.env.example` | Documentation-only defaults; each implemented module owns real local configuration |
| `Makefile` | Python-standard-library repository validation and regression tests |
| `.github/` | Issue/PR templates, CODEOWNERS and pinned-action repository CI |
| `scripts/repository/` | Metadata validation, issue rendering and explicit publication |
| `tests/repository/` | Repository-tool tests only; no implied product coverage |
| `docs/` | Preserved source specs/PDF, approved task contracts, architecture, instructions and published issue map |

## Independent module roots

The [task register](task-register.md) lists all task-owned roots and their owning task. Parent directories group purpose rather than shared builds:

| Parent | Components |
| --- | --- |
| `apps/` | `api`, `web` |
| `services/` | `simulator`, `policy`, `evidence`, `workflow`, `action-ledger`, `dispatcher`, `verifier`, `voice`, `finharness-runtime`, `merchant-settlement`, `merchant-inbox`, `merchant-refunds`, `merchant-disputes`, `merchant-sla`, `merchant-analytics`, `merchant-teams` |
| `packages/` | `contract-checks`, `persistence`, `approval-ui`, `telemetry`, `finharness-sdk`, `indic-context`, `finharness-telemetry`, `merchant-comms` |
| `tooling/` | `workspace` |
| `integration/` | `core` |
| `evals/` | `core` |
| `replay/` | `core`, `finharness` |
| `benchmarks/` | `finbench_indic` |
| `release/` | `mvp` |
| `validation/` | `sandbox-pilot` |

Each root starts with `AGENTS.md`, `README.md` and `CHANGELOG.md`. These are scaffolding and task instructions, not applications. No empty source hierarchy, dummy endpoint, stub check target or fabricated package version is supplied to imply implementation.

## Implemented Python module layout

Use a task-local layout such as:

```text
<owned-root>/
  AGENTS.md
  README.md
  CHANGELOG.md
  pyproject.toml
  uv.lock                     # or the locally selected reproducible lock mechanism
  Makefile                    # check/setup/run as applicable
  .env.example
  src/sentinel_<component>/
    domain/                   # actual framework-free rules and types
    application/              # use cases and narrow ports
    adapters/                 # HTTP/PostgreSQL/provider/clock/telemetry boundaries
    bootstrap.py              # config and dependency wiring
  contracts/                  # pinned wire snapshots and compatibility examples
  tests/
    unit/
    contract/
    integration/              # local DB/peer tests where needed
    stubs/
  migrations/                 # only this component's state
  compose.yaml                # only if a local database/peer container is useful
```

Create folders only when code/tests justify them. Pure tools/libraries may flatten the source structure. Financial schemas remain owned by the ledger; persistence helpers do not centralize its tables.

## Implemented TypeScript module layout

The web app owns its Next.js routes and API composition; the approval package owns typed components and a standalone preview. Each has its own `package.json`, selected lockfile, `tsconfig.json`, local checks, configuration example, tests and contract fixtures. Keep business transformations separate from rendering/network clients. Do not deep-import host-app routes or another module's internals.

The shell supplies typed slots; a local substitute enables isolated development. The real approval component may be selected during assembly through its public boundary. Optional voice stays disabled without a voice implementation.

## Files shared across agents

Component agents edit their module's changelog/docs, not global files. The only extra task-owned root path is `.github/workflows/module-checks.yml` for SN-001. Existing `repository.yml` validates repository metadata independently and remains a coordinated maintenance boundary.

Do not add a root application manifest, global application lockfile, shared migration chain or broad parent-directory ownership. Changes to task scope/ownership/contracts must be reviewed and mirrored in affected issues. There is no generated index that agents must regenerate on every component edit.
