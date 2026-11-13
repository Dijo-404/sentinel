# GitHub agent workflow administration

## Sources of truth

- GitHub issues: live status, accountable human, active agent/session, blockers, progress and PR/evidence.
- `docs/tasks.json`: versioned scope, owned paths, interfaces, contract hashes and acceptance.
- `docs/task-issues.json`: stable task-to-issue number/URL mapping only; no live status/assignment.
- `docs/task-register.md`: human-readable module/issue index.

## Labels

`agents` selects the shared queue. Exactly one `status:*` belongs on each task. Lanes A–D, priorities P0/P1, phases 1/2 and `optional` describe scope/priority. All tasks may be ready together. Neither issue ordering nor phase requires another implementation to finish.

Status definitions, claims, updates and owner merge policy are in [CONTRIBUTING.md](../CONTRIBUTING.md). General new-task templates start in backlog until a self-contained contract/root is supplied; the approved 26 briefs are complete enough to admit together.

## Render and publish

```sh
make check
python3 -m scripts.repository.tasks --base-commit <full-reviewed-commit-sha>
```

Review `.artifacts/github-tasks/SN-NNN.md`. Every rendered brief contains scope/paths, contract version/hash, exact module command to implement, test/evidence expectations and the complete pinned contract text. Nothing is sent without `--publish`.

```sh
python3 -m scripts.repository.tasks --base-commit <full-reviewed-commit-sha> --publish
```

The publisher checks all open/closed issues and uses a stable body marker or `[SN-NNN]` title. It rejects duplicate/conflicting identities, creates missing labels/issues, and preserves existing issue bodies/status/assignment. It checkpoints ignored publication metadata after each task and writes the tracked issue map after completion. Rerun after a partial failure; never delete/recreate tasks to recover.

For scope changes, update the versioned plan and affected issue through coordinated review; ordinary publication intentionally does not overwrite active task descriptions. Existing label descriptions/colors are preserved.

## Empty-repository bootstrap

The user authorized the initial setup, including establishing main. A reviewed local baseline commit supplies stable contract/source links. Initial issues may be created as backlog before the first push using `--initial-status status:backlog`; they are activated together only after main is published. The issue register/maps can therefore be included in the first push without bypassing an established main protection rule.

After initial main exists, every component and repository-maintenance change uses a PR. The bootstrap exception expires. Do not infer future permission to push main from this initial setup.

## Checks and main protection

`Repository checks` is the baseline CI job. It runs root `make check` and does not wait for product modules. SN-001 may later add independently discovering module checks; missing components must not fail unrelated task PRs.

The owner reviews and merges. Where GitHub supports the configured private repository, main protection should require PRs, this actual status check, no force pushes/deletions, and resolved conversations. Do not require an impossible self-approval for a sole-maintainer bootstrap. CODEOWNERS records the maintainer; its presence alone does not enforce reviews or restrict merges.

Inspect actual applied rules and CI results; do not claim a protection feature was installed when the API rejects it. A private-repository plan limitation leaves the documented owner-review policy in force but not platform-enforced. Record the API outcome in setup evidence/final handoff.

## Saved Agents view

Use `repo:Dijo-404/sentinel is:issue is:open label:agents`. The inspected API did not provide a supported saved-view endpoint. Existing view configuration therefore remains unverified; the [equivalent queue](https://github.com/Dijo-404/sentinel/issues?q=is%3Aissue%20is%3Aopen%20label%3Aagents) is the supported entry point supplied by this baseline.
