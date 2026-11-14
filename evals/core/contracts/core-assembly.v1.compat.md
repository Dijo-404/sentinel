# core-assembly.v1 compatibility checklist (SN-016 consumer)

Pinned baseline: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

| Case | Stub | Expected evaluator behavior |
| --- | --- | --- |
| valid | `tests/stubs/core_assembly/valid.json` | real-peers probe OK; evaluation may proceed |
| unavailable | `tests/stubs/core_assembly/unavailable.json` | fail closed `PEER_UNAVAILABLE`; no fixture fallback |
| malformed | `tests/stubs/core_assembly/malformed.json` | fail closed `PEER_MALFORMED` |
| unauthorized_or_out_of_scope | `tests/stubs/core_assembly/unauthorized_or_out_of_scope.json` | fail closed `PEER_UNAUTHORIZED` |

Local reference peers: `StubAssemblyPeer` under `tests/stubs/`.
HTTP path: `HttpAssemblyPeer` probes `/v1/capabilities` when `assembly_stub=live` + URL.
Full product safety certification against a live assembled stack remains owner-run.
Fixture-only assembly evidence is not release evidence.
