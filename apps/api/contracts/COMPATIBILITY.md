# SN-040 case-api principal catalog compatibility

Pinned baseline: `sentinel.task-contracts.v1` /
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Additive human principals

Fixture maps (`fixtures/auth_tokens.json`, `fixtures/identity_sessions.json`)
now include `merchant`, `risk_officer`, and `platform_admin` for peer catalog
alignment with identity SN-035 / roles.md §1.1.

## Decide path (unchanged SN-007)

`POST /v1/ops/actions/{action_id}/decisions` still requires exact role
`supervisor`. Extended humans MUST receive 403 and MUST NOT cause a ledger
peer call.

Forbidden for these roles (and any non-supervisor human):

- `financial.approval.decide`
- ledger reserve / provider write (case-api never grants these)

Do not alias `platform_admin` → supervisor or sandbox-admin.
