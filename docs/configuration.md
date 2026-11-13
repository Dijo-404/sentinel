# Configuration ownership

## Repository tooling

Repository checks use Python's standard library and GNU Make. `PYTHON` may override the interpreter, for example `make check PYTHON=python3.12`. Publication additionally needs Git, authenticated `gh`, repository issue/label permissions and a reviewed full commit SHA.

The root `.env.example` documents intended development defaults only. Repository tooling does not load it, and copying it does not start services or enforce a payment kill switch. Runtime enforcement must be implemented and tested by the owning component.

## Component configuration

Each module owns its configuration schema, ignored local env file, tracked `.env.example`, startup validation, manifest/lockfile and documented setup. Classify variables as public UI, secret server-side, local fixture or deployment configuration. Fail startup for malformed required real-peer configuration. Do not require optional external credentials for standalone local checks.

Use explicit fixture versus real-peer modes. In real-peer mode, unavailable or unauthorized required peers produce a clear error; do not default to fake success. Optional voice/context may stay disabled. Inject clocks, model/provider clients, evidence/policy/ledger ports and exporters through composition, not process-global state hidden inside domain code.

## Secrets and public configuration

- Commit examples, never tokens, passwords, signing keys, private transcripts or customer records.
- `NEXT_PUBLIC_*` is browser-visible; no provider/model/voice secret belongs there.
- Local fixture tokens are synthetic, explicitly scoped test identities. Real integrations use separately approved credentials and cannot accept fixture credentials.
- Keep databases/simulators private to the local test network unless a separately reviewed interface requires exposure.
- Redact logs/errors and keep bounded metric labels. Never print environment dumps in checks or GitHub comments.

## Database and money controls

Each stateful service owns schema/credentials/migrations. The ledger alone owns authoritative financial transaction state and validates exact scope, evidence, policy, approval, balances and original destination. An env flag is an additional kill switch, never a replacement for authorization.

Keep provider references and in-flight case/runtime versions stable across config changes. Disabling new writes does not abandon unknown outcomes or stop authorized reconciliation. Reset/seed tools must require a sandbox environment and refuse non-demo data.

## GitHub configuration

The [workflow guide](github-workflow.md) documents labels, publication, branch/review policy and platform limits. Saved views do not dispatch agents. Do not enable auto-merge or change task ownership as a side effect of setup reruns.
