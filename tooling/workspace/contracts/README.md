# module-checks.v1 snapshot

Pinned input: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
The relevant baseline port says: discover declared modules already present, run
module-local checks, and report absent modules separately, without a global
dependency install. This tool consumes no service ports.

`src/sentinel_workspace/contracts.py` is the typed snapshot. The JSON report has
`contract_version: module-checks.v1`, `baseline_version`, `baseline_sha256`, and
`modules`. Each module has `id`, repository-relative `root`, `status`, nullable
integer `exit_code`, and bounded captured `output`. Additional optional report
fields are compatible. Unsupported CLI commands and malformed declarations fail
explicitly with exit 2; no fixture substitution occurs.

Status semantics:

| Status | Meaning |
| --- | --- |
| READY | Directory and Makefile present; discovery did not execute the check |
| ABSENT | Declared module directory absent; no success claimed |
| UNIMPLEMENTED | Directory exists without a Makefile; no success claimed |
| SKIPPED | Excluded by explicit module/changed-path selection |
| PASS | The selected module's real `make check` exited 0 |
| FAIL | The selected module's `make check` exited nonzero |
| TIMEOUT | Check exceeded the configured wall time; process group killed |
| OUTPUT_LIMIT | Check exceeded captured-byte limit; process group killed |
| ERROR | Make could not start; no fixture fallback |

Exit 0 means no **executed** checks failed, including when no checks were run.
Exit 1 means at least one FAIL/TIMEOUT/OUTPUT_LIMIT/ERROR. Missing/unimplemented
modules are informational so unrelated component PRs remain independent. This
is not a release or assembly acceptance gate.

Compatibility checklist for real repositories:

- Use a JSON task list with unique `SN-NNN` ids and normalized, disjoint roots.
- Preserve module-local `make check`; optional `standalone.check_command` must
  match `make -C <root> check` exactly. Commands are not read as shell input.
- Keep Makefiles inside the repository; escaped/aliased roots are rejected.
- Module checks install/prepare only their own locked dependencies, or CI sets
  them up explicitly before selecting that module.
- Capture every status; never turn ABSENT/UNIMPLEMENTED/SKIPPED into PASS.
- Run real-component assembly separately; no HTTP peer/authentication, database,
  payment adapter, or model is involved in this interface.
