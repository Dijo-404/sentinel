# SN-040 action-ledger principal catalog compatibility

Pinned baseline: `sentinel.task-contracts.v1` /
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Additive human roles

`merchant`, `risk_officer`, and `platform_admin` appear in the local token map
(`contracts/principals.json`, `demo_principals` aliases) so peers can resolve
authenticated humans. Catalog presence is **not** authority.

| Route family | Allowed roles (unchanged) | Extended humans |
|---|---|---|
| `POST .../decisions` | `supervisor` only | risk_officer / platform_admin / merchant → 403 |
| `POST .../reservations` | `workflow` | extended humans → 403 |
| `POST .../claims` / provider outcomes | `dispatcher` | extended humans → 403 |

Do not map `platform_admin` to `sandbox-admin` or elevate risk/merchant to
supervisor. Existing SN-009 contract semantics preserved (versioned additive only).
