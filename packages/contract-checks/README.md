# SN-002 — Portable contract conformance checks

This installable Python tool checks the supplied `sentinel.task-contracts.v1` baseline without another Sentinel package, server, database, provider credential, or model. Its output is local conformance evidence, never payment authority or assembled product evidence.

Owned root: `packages/contract-checks/`. Branch: `feat/sn-002-contracts`.
Baseline SHA-256: `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

## Standalone setup and check

Requires Python 3.11+, GNU Make and `uv`. Dependencies are pinned in `pyproject.toml` and `uv.lock`; setup installs only this module. The first setup needs access to the configured Python package index, or an already populated local cache.

```sh
cd packages/contract-checks
make setup
make check
make run
```

`make check` runs 26 unit/CLI tests and a structured fixture report: 97 valid/invalid wire fixtures, 8 canonical byte/digest vectors, 7 malformed JSON cases, 2 compatibility comparisons, 2 retry captures and the pinned baseline hash (117 checks). All data and inference are synthetic/local; no peers, payment writes or model calls occur. `.env.example` documents that no environment configuration or secrets are read. Input paths are explicit CLI arguments.

From the repository root, run `make -C packages/contract-checks check` and the separate root `make check`. The root check validates repository metadata only.

## CLI

Run these commands from this module:

```sh
uv run --locked sentinel-contracts check
uv run --locked sentinel-contracts digest src/sentinel_contract_checks/data/refund-action.json
uv run --locked sentinel-contracts validate RefundAction src/sentinel_contract_checks/data/refund-action.json
uv run --locked sentinel-contracts compare src/sentinel_contract_checks/data/compat-before.json src/sentinel_contract_checks/data/compat-optional.json
uv run --locked sentinel-contracts compare src/sentinel_contract_checks/data/compat-before.json src/sentinel_contract_checks/data/compat-breaking.json
uv run --locked sentinel-contracts retries src/sentinel_contract_checks/data/retries-conflict.json
```

The last two commands intentionally exit 1. `compare` returns `IDENTICAL`, `COMPATIBLE_OPTIONAL` or `BREAKING`, with changed schema paths. `validate` and `retries` return structured `path`, `code`, `message` violations. `check` returns a baseline `RunReport` explicitly labeled `mode: fixture`. Every successful command exits 0; invalid inputs, payload conflicts and breaking changes exit 1. `python -m sentinel_contract_checks` offers the same interface. `-` reads JSON from stdin.

`validate Evidence envelope.json --evidence-bytes original-facts.json` additionally checks SHA-256 over the exact supplied bytes and confirms the parsed typed facts match the envelope. It never reserializes the original bytes before hashing. This adapter defines the evidence payload as its typed `facts` object; a producer with a different snapshot wrapper must extract and validate that wrapper explicitly. Digest equality does not authenticate the source or prove freshness.

`retries` checks an array of `{ "scope": "synthetic capture label", "key": "stable-key", "type": "ReservationRequest", "value": { ... } }`. Repeated scoped keys and types must contain identical JSON values, independent of object-key order. Array order remains significant. Scope labels are capture metadata, never authenticated principals. This is a stateless fixture checker; it creates no idempotency store, reference, reservation or ledger.

## Portable snapshots and exported functions

The installed package includes:

- [schemas.json](src/sentinel_contract_checks/data/schemas.json): JSON Schema 2020-12 definitions for all 66 named baseline types, including six exact action variants, typed evidence facts, policy/approval, ledger commands, cases/events, workflow/model, verification, CLI reports, voice and route wrapper records.
- [baseline.md](src/sentinel_contract_checks/data/baseline.md): the byte-exact pinned source, checked by SHA-256.
- [routes.json](src/sentinel_contract_checks/data/routes.json): 31 exact method/path, request/response and role rows. The baseline also records common health/readiness/capabilities routes and authentication/resource-scope obligations.
- [fixtures.json](src/sentinel_contract_checks/data/fixtures.json), [canonical-vectors.json](src/sentinel_contract_checks/data/canonical-vectors.json) and [baseline-examples.json](src/sentinel_contract_checks/data/baseline-examples.json): synthetic portable inputs, exact canonical strings/digests, and unchanged operation examples.

Public functions are `validate`, `canonical_action`, `action_digest`, `verify_evidence`, `check_retries`, `compare_schemas`, `load_json`, `snapshot` and `fixture_report`. They return JSON-compatible values, bytes or structured violations and use no filesystem/network state outside the installed snapshot resources. CLI filesystem/stream handling lives in `cli.py`.

Actions reject undeclared fields, unknown variants, missing fields, monetary floats, booleans used as integers, invalid destinations and nonpositive amounts/revisions. Canonicalization preserves Unicode without normalization and preserves array order. The supplied refund vector hashes to `d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993`.

Readers enforce the exact declared schemas: optional means omitted, not `null`. The baseline's compatible optional evolution is reported by comparing a candidate schema; it does not silently widen the pinned financial payload. Compatibility classification is conservative: only added optional nonfinancial properties and added definitions qualify. Changed versions, required fields, enums, constraints and financial/action fields require versioned review. Some harmless schema rewrites may therefore report `BREAKING`.

## Integration checklist and limits

Before adopting a peer contract:

- Compare the reviewed candidate schema, preserve exact financial fields and canonical vectors, and version breaking changes.
- Feed original JSON bytes through `load_json`; generic JSON Schema validators can accept `1.0` as an integer, while this tool deliberately rejects all numeric floats. Duplicate keys, nonfinite numbers and invalid UTF-8/surrogates also fail.
- Check embedded action digests and matching approval digest/revision/policy fields. Keep original evidence bytes; do not infer their digest from reconstructed JSON.
- Authenticate the actual peer, enforce tenant/subject/case/role scope, and reject unavailable, unauthorized, malformed or incompatible responses. Missing peers must remain failures; this tool has no network adapter or fallback mode because SN-002 consumes no peer port.
- Enforce freshness at authorization using the server's clock, financial limits under the ledger transaction, approved state transitions and separate provider/credit evidence before closure. This tool validates state enums, local expiry ordering, model proposal presence and resolved-result assessment presence; it cannot prove these runtime obligations.

No PostgreSQL, migration, peer double or concurrent execution is needed for this stateless module. Services remain responsible for authenticated scope, expiry against current time, durable idempotency, 409 responses, HMAC signatures, atomic reservation and state/closure transitions. The route snapshot documents those boundaries; it does not implement service endpoints. Real-component integration, payment simulation, inference and product assembly are unverified here. The owner reviews and merges the SN-002 PR; this component does not establish release acceptance.
