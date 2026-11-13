# SN-001 — Independent module discovery and checks

Optional Python CLI implementing `module-checks.v1`. It reads declared module
roots from `docs/tasks.json`, reports absent/scaffold modules separately, and
runs selected module-local `make check` commands. It installs no sibling
packages and creates no global dependency graph.

Owned paths: `tooling/workspace/**` and `.github/workflows/module-checks.yml`.
Branch: `feat/sn-001-workspace`. No task-completion prerequisites.

## Standalone setup and checks

Requires Python 3.11+, GNU Make and a POSIX host for process-group cleanup.
The CLI and tests use only the standard library. Installation uses uv (tested
with 0.13.7), the local `pyproject.toml`/`uv.lock`, and a pinned setuptools build
backend; initial installation may download that backend. No provider secrets,
Sentinel services, databases, Docker, root install or peer packages are needed.

```sh
cd tooling/workspace
uv sync --locked
make check PYTHON="$PWD/.venv/bin/python"
.venv/bin/sentinel-modules discover --repo tests/fixtures/mini-repo
```

The source-tree checks also work without uv, installation or network:

```sh
make -C tooling/workspace check
make -C tooling/workspace preview
```

Copy this directory anywhere and run the same commands to prove isolation. The
`tests/fixtures/mini-repo` repository contains a passing synthetic module with
its own manifest/lockfile, an intentional failing module, a scaffold, and a
declared absent module. Tests copy the repository to temporary directories;
they do not modify fixtures or inspect sibling implementations.

The sample component works without the aggregator:

```sh
cd tests/fixtures/mini-repo/modules/good
uv sync --locked
make check
```

That manual sample command creates `checked` in the sample directory; remove
that file afterward. It is synthetic check evidence only.

## Discover and run

From the repository root after standalone installation:

```sh
tooling/workspace/.venv/bin/sentinel-modules discover --repo .
tooling/workspace/.venv/bin/sentinel-modules check --repo . --module SN-001
# Optional: run every declared module that has a Makefile.
tooling/workspace/.venv/bin/sentinel-modules check --repo .
```

JSON reports preserve module id/root, status, exit code and combined captured
stdout/stderr. `READY` means a Makefile exists; the check target is validated by
execution, so a Makefile without `check` produces FAIL. `ABSENT` and
`UNIMPLEMENTED` are informational, never PASS. `SKIPPED` marks modules outside
selection. Exit 0 means no executed checks failed, even when nothing ran;
exit 1 means a check failed; exit 2 means invalid input/configuration.

Defaults are `--tasks docs/tasks.json`, `--timeout 300` seconds per module, and
`--max-output-bytes 65536`. The output limit counts captured raw bytes; invalid
UTF-8 is replaced when rendering JSON. A timeout or output-limit violation
kills the process group, records TIMEOUT/OUTPUT_LIMIT, and continues unrelated
checks. An unavailable Make executable records ERROR; no fixture fallback
exists. `.env.example` documents defaults; dotenv files are not loaded.

All task declarations are validated before any check starts: unique ids,
normalized disjoint roots, repository containment, no symlink escapes/aliases,
and the fixed module-local `make check` command. Extra task fields are accepted
for compatibility. Makefiles are trusted repository code, not sandboxed code;
checks inherit the caller's environment. The aggregator does not print it.

PR selection accepts NUL-separated changed paths (including deleted paths):

```sh
git diff --no-ext-diff --name-only -z --no-renames main HEAD > /tmp/sentinel-changes.bin
tooling/workspace/.venv/bin/sentinel-modules check --repo . --changed-paths /tmp/sentinel-changes.bin
```

`--no-renames` includes both sides of a move. Selection uses each task's root
and declared extra owned paths. Combine with repeated `--module` flags to take
the intersection. Unrelated documentation changes execute no component checks.

## CI and component setup

`.github/workflows/module-checks.yml` uses pinned checkout/Python actions,
read-only permissions and no provider secrets. It installs this module alone,
runs its self-tests, reports all declarations, and checks changed modules on
PRs (all runnable modules on main/manual runs). It never edits manifests or
runs a global install. Each selected module must prepare its own dependencies
in `make check` or provide a dedicated CI setup step. Initial package downloads
require network access; product inference and payment access are not used.

For a component with uv-managed dependencies, its dedicated workflow may use:

```yaml
# After checkout, Python and uv setup; replace <owned-root> with a literal path.
- run: uv sync --locked --project <owned-root>
- run: make -C <owned-root> check
```

This is an example, not a cross-module build graph. Other languages own their
own locked installation command. This aggregator does not guess setup steps,
start services, or certify a module's test adequacy.

## Contract, verification and limits

Pinned input: `sentinel.task-contracts.v1`, SHA-256
`0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.
See [typed snapshot and compatibility checklist](contracts/README.md).
No consumed service ports, auth API, database migrations or peer stubs apply;
the subprocess adapter runs actual local Makefiles against synthetic inputs.

The 16 acceptance/negative tests cover module execution, absence/scaffolds,
failure continuation, changed/deleted/extra paths, invalid/unknown input,
nonstandard commands, duplicate/overlapping/escaped/aliased roots, unavailable
Make, missing check target, output/time limits and child-process cleanup.
Root `make check` remains repository metadata validation only.

Standalone tests prove this tool using local fixture modules. Real application
components, payment simulators, live/fake inference, product assembly, release
and external pilot behavior are unverified and outside this task. Missing or
unimplemented modules cannot establish release readiness. The owner reviews
and merges the PR; this component does not modify root policy or sibling state.
