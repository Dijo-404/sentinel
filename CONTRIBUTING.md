# Contributing to Sentinel

## Start with a task

Use the [Agents queue](https://github.com/Dijo-404/sentinel/issues?q=is%3Aissue%20is%3Aopen%20label%3Aagents), [task register](docs/task-register.md), and [AGENTS.md](AGENTS.md). The owner-created saved view should use:

```text
repo:Dijo-404/sentinel is:issue is:open label:agents
```

The saved view's identifier/filter was not available through the inspected API. Use the equivalent queue immediately; no dispatcher or automatic claim/merge bot is installed.

Every component can start from the same baseline. Phase, priority and lane do not impose ordering. Use local stubs for consumed ports; zero task-completion prerequisites are allowed. Optional Phase 2 implementation may start now while activation remains a separate product decision.

## Status and ownership

| Label | Meaning |
| --- | --- |
| `status:backlog` | Scope, contracts or admission need work; no predecessor gate. |
| `status:ready` | Self-contained scope/contracts/root are supplied; available to claim. |
| `status:in-progress` | One agreed owner and agent/session are working. |
| `status:blocked` | An actual environment/scope/contract blocker and next action are recorded. |
| `status:review` | PR and standalone evidence are ready for owner review. |
| `status:done` | PR merged and component evidence accepted; issue closed. |

Keep exactly one status. Lane A is backend/workflow; B simulation/safety; C product/language; D tooling/observability/evaluation. These are responsibility categories, not assigned people. Keep one active task per human/agent pair; document an explicit handoff or non-conflicting replacement if blocked.

## Claim safely

Authenticate `gh` with the accountable human's account. Replace the example issue number:

```sh
task_issue=123
gh issue view "$task_issue" --repo Dijo-404/sentinel --comments
gh issue view "$task_issue" --repo Dijo-404/sentinel --json assignees,labels
gh issue edit "$task_issue" --repo Dijo-404/sentinel --add-assignee @me
gh issue view "$task_issue" --repo Dijo-404/sentinel --comments
```

Assignment is not a lock. If another owner/claim exists, resolve it before editing. Do not remove another assignee or assume a stale-looking task is abandoned. Post a completed claim using `--body-file`:

```text
Claim: <human GitHub account>, agent <name/session>, <UTC timestamp>
Task: SN-NNN
Branch/worktree: <listed branch and isolated path>
Owned root and extra listed files: <paths>
Contract version/hash: <pinned baseline>
Local peer doubles: <consumed ports and fixture locations>
Next: <acceptance criterion>
Next update: <time within one working hour>
```

```sh
gh issue comment "$task_issue" --repo Dijo-404/sentinel --body-file /tmp/sentinel-claim.md
gh issue edit "$task_issue" --repo Dijo-404/sentinel --remove-label status:ready --add-label status:in-progress
git fetch origin
git worktree add ../sentinel-sn-NNN -b feat/sn-NNN-short-name origin/main
```

Use the actual branch listed on the issue. If already in an isolated worktree, keep it and record the path. Do not switch a teammate's checkout. If the listed branch is already owned, agree on another branch rather than force-pushing or attaching a second active agent.

## Build independently

Read the scoped module guide and contract snapshots. Own local manifests/lockfiles, configuration, migrations, fixtures, tests and docs. Provide `Makefile` target `check` and a local run/preview command. Use the [architecture](docs/architecture.md) and [testing](docs/testing.md) guidance. A module may use its own PostgreSQL/container setup; it must not require another task's implementation or a global workspace install.

Do not wait for optional repository aggregation, validators, database helpers or peer services. Test real-peer adapters using local controlled peers. An absent peer is expected during development; an incompatible published baseline or unusable local environment is an actual blocker.

For a shared contract change, preserve the baseline endpoint/type, publish additive/versioned changes and compatibility fixtures, and notify affected task issues. Updating root planning policy or ownership requires a separately coordinated change; component tasks do not race over root files.

## Progress and handoff

Post updates on transitions and at least once per working hour:

```text
Task/status; human; agent/session; UTC time:
Branch/worktree; last pushed commit/PR:
Owned paths; contract hash:
Completed:
Standalone checks and actual results:
Assembly evidence: real components | fixtures | not exercised
Blocker and accountable next owner:
Next action and next update:
```

Keep the issue accurate if the agent stops. A private todo/memory file is not a handoff. Do not publish real customer records, credentials, raw transcripts or unredacted provider payloads.

## PR, review, and close

Integrate current `origin/main` without overwriting another branch, resolve conflicts and rerun relevant checks. Keep the PR confined to the task's paths. Use the PR template, include `Refs #N`, and distinguish module checks from actual assembled evidence.

```sh
make check
make -C <owned-root> check
git push -u origin <task-branch>
gh pr create --repo Dijo-404/sentinel --base main --title '<clear outcome>' --body-file /tmp/sentinel-pr.md
gh issue edit "$task_issue" --repo Dijo-404/sentinel --remove-label status:in-progress --add-label status:review
```

The root check exists in the baseline; the module target is implemented by its task. Never claim a nonexistent command passed. The repository owner reviews/merges; agents never merge, enable auto-merge or push application work to main. After merge and accepted component evidence, replace review with done and close the issue. There is no downstream-readiness queue to unlock.

The owner later selects compatible real component versions for integration/release. SN-014, SN-019 and SN-026 deliver independent verification tools; completing those issues does not claim a shipped product or successful external pilot.

## Changelog and maintenance

Update the owned module's `CHANGELOG.md` under `Unreleased` in every behavior/config/contract change. Describe observable changes, validation and limits. Root `CHANGELOG.md` is maintained through coordinated repository/release changes; 26 agents must not edit it simultaneously. Do not choose an open-source license or publish a package without owner authorization.

## Repository maintenance commands

```sh
make check
python3 -m scripts.repository.tasks --base-commit <full-reviewed-commit-sha>
python3 -m scripts.repository.tasks --base-commit <full-reviewed-commit-sha> --publish
```

Rendering is local. `--publish` explicitly creates missing labels/issues through `gh`; it preserves existing issue body/status/assignment, including closed tasks and renamed titles with stable markers. Duplicate identities fail closed. Do not run publication to reset or regenerate live tasks. Review scope changes through PRs and affected issues.
