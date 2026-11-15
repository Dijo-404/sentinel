# SN-040 policy principal catalog compatibility

Pinned baseline: `sentinel.task-contracts.v1` /
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

Additive fixture entries for `merchant`, `risk_officer`, `platform_admin`,
and `sandbox-admin` exist for peer catalog alignment. `POST /v1/evaluate`
remains workflow-scoped (ledger uses a workflow service principal). Extended
humans MUST NOT receive evaluate, `financial.approval.decide`,
`ledger.reserve`, or provider-write permissions.

`GET /v1/policies` is a read-only artifact catalog (seed
`demo-policy-v1`). Allowed roles: `platform_admin`, `workflow`,
`sandbox-admin`. It does not mutate evaluate rules.
