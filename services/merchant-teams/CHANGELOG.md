# SN-034 / SN-039 changelog

## Unreleased

### Added

- SN-039: identity.v1 membership client port, fixture stubs under
  `tests/stubs/identity/`, HTTP adapter, and `POST /v1/staff/sync` projection
  into the local staff store. Platform Admin / identity owns grants;
  merchant-teams does not create competing platform roles.
- `GET /v1/merchant/team` projection surface over local projected staff;
  auto-syncs when identity peer configured; response `source` labels
  `identity_projection` or `local_projection`.
- Optional `IDENTITY_BASE_URL` / `IDENTITY_TOKEN` in real-peers; fail closed
  when configured identity is unavailable, unauthorized, or malformed.
- AUTH-09 / AUTH-10 acceptance coverage: merchant approver cannot authorize
  ledger money; merchant admin cannot grant platform roles.

### Changed

- Sync deactivates local staff not present in the identity membership
  response (`MEMBERSHIP_REVOKED`).
- real-peers + `IDENTITY_BASE_URL`: local create / display-name / role
  mutations rejected as projection-only (`CONFLICT`).
- Merchant staff roles remain viewer / operator / approver / admin only;
  platform authorities (`platform_admin`, `supervisor`, `risk_officer`, …)
  are rejected at normalize/project boundaries.

## Prior

- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Added (SN-034)

- Independent `merchant-teams.v1` HTTP service: staff CRUD/deactivate, role
  assignment, advisory approval limits, append-only activity timeline.
- Local `case-api.v1` stubs (`valid`, `unavailable`, `malformed`,
  `unauthorized_or_out_of_scope`) and fail-closed HTTP real-peer adapter.
- Contract snapshots, principals, compatibility checklist, `.env.example`,
  Makefile `check`/`preview`, and acceptance tests proving advisory limits
  never authorize ledger/provider writes and unauthorized scope fails closed.
- Contract pin: `sentinel.task-contracts.v1` SHA-256
  `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
