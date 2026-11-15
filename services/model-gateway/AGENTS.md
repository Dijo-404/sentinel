# Scoped agent rules: model-gateway

Read [repository AGENTS.md](../../AGENTS.md) and this module's [README](README.md) before
editing. These rules supplement the root instructions.

## Ownership

- Work only in `services/model-gateway/` and any exact extra paths listed in the task.
- Own the module's manifest/lockfile, configuration, code, tests, README and changelog.
- Do not edit the callers (`services/workflow`, `services/assistant`) or `services/knowledge`
  from this module. The wire contracts are pinned in `tests/contract/`.

## Architecture and contracts

- Grounding rules live in `domain/grounding.py`: money, currency, destination, case and
  revision come from the request and evidence, never from model text.
- Use cases depend on the `ChatModel` and `KnowledgeSearch` ports. Sarvam and knowledge HTTP
  stay in `adapters/`.
- Runtime has no fake or fixture model. Test doubles stay under `tests/`.
- Never log or commit `SARVAM_API_KEY`. No money authority: this module only proposes.

## Checks and handoff

- Run `make -C services/model-gateway check`. `make live-test` makes real Sarvam calls and is
  never part of `check`.
- Update [CHANGELOG.md](CHANGELOG.md) and record live versus doubled evidence in the PR.
