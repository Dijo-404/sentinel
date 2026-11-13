# Testing and evidence

## Repository baseline checks

Run `make check` with Python 3.11+ and GNU Make. It runs metadata/docs validation and standard-library regression tests. It needs no product packages, PostgreSQL, Docker, model key or payment credentials.

The validator checks zero task prerequisites, disjoint owned roots/paths, contract hashes, declared peer stubs, absence of hidden required Phase 2 peers in the MVP, issue references, module instructions and local links. Tool tests cover unsafe metadata and stable GitHub issue identities.

## Required component proof

Each task must implement `make -C <owned-root> check`. The target must pass with all other Sentinel task implementations removed/unavailable, using only the owned module, supplied contract inputs and explicit local doubles. A module may start its own PostgreSQL or local peer container with documented setup/cleanup; it cannot depend on another agent's server.

- Unit tests exercise real deterministic rules and use cases.
- Contract tests exercise declared wire types, canonical digest fixtures, errors, authenticated scope and compatible/unsupported versions.
- Adapter tests use controlled local peers for valid, unavailable, malformed and unauthorized/out-of-scope responses. Real-peer failure cannot silently select fixtures.
- Stateful tests use a real local PostgreSQL instance where transaction/locking/checkpoint behavior matters. In-memory mocks cannot prove refund reservation concurrency.
- UI checks cover keyboard interaction, input/error/loading/empty states, scope restrictions, stale decisions and exact status wording.

Write meaningful behavior/failure tests before changing nontrivial logic. Avoid tests that repeat the implementation or claim correctness from a snapshot alone. Keep credentials optional for fake-model/voice local checks; report live inference separately.

## Financial acceptance

Test over-refund concurrency, wrong scope/role, expired/mismatched approval, pending/failed capture, invalid destination, stale/conflicting evidence, timeout-after-accept, crash-after-submit, duplicate/out-of-order webhook, unknown outcome and false-credit closure. Track completed + pending + reserved money under the ledger transaction. Reconciliation must retain the original reference and reservation.

Financial audit failure blocks creation of new commands without losing durable reconciliation work. Prompt injection, hallucinated IDs or client headers cannot grant authority. Test these behaviors at the actual boundary, not just a prompt template.

## Evidence labels and independence

Record exact command, environment, commit/version, contract hash, observed result and redacted artifact links. Separately identify:

| Dimension | Values |
| --- | --- |
| Component under test | Real implementation or local reference peer |
| Payment provider | Simulator or separately authorized external sandbox |
| Model/voice | Fake/recorded or actual live call |
| Run | Standalone, assembled components, replay or external pilot |

Passing fixture tests proves the tested component behavior under those fixtures. It is not evidence of product assembly, production safety, bank credit or a live provider integration. Report actual fixture counts/denominators, holdout grouping and measured model cost/latency only when run.

## Assembly and release

The owner runs SN-014's runner against selected real component versions, SN-019's release evidence kit, and any separately authorized pilot tooling. Strict mode rejects missing/incompatible components, failed checks and fixture-only substitutes. Tool self-tests include positive and negative synthetic manifests so tool implementation can finish independently of product services.

Required release evidence covers four payment journeys, tenant/approval boundaries, real PostgreSQL concurrency, timeout recovery, webhook/rechecks, trace correlation, evaluation and replay. Optional voice and Phase 2 are not required for MVP acceptance.
