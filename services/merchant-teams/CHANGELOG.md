# SN-034 changelog

## Unreleased

### Added

- Independent `merchant-teams.v1` HTTP service: staff CRUD/deactivate, role
  assignment, advisory approval limits, append-only activity timeline.
- Local `case-api.v1` stubs (`valid`, `unavailable`, `malformed`,
  `unauthorized_or_out_of_scope`) and fail-closed HTTP real-peer adapter.
- Contract snapshots, principals, compatibility checklist, `.env.example`,
  Makefile `check`/`preview`, and acceptance tests proving advisory limits
  never authorize ledger/provider writes and unauthorized scope fails closed.
- Contract pin: `sentinel.task-contracts.v1` SHA-256
  `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
