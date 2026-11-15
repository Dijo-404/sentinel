"""Render task issues; publish only with explicit --publish using authenticated gh."""

import argparse
import hashlib
import json
import re
import subprocess

from scripts.repository.validate import REPOSITORY_ROOT, validate_repository

REPOSITORY = "Dijo-404/sentinel"
LABELS = {
    "agents": ("7057ff", "Independently buildable agent task"),
    "status:backlog": ("ededed", "Scope or publication pending; not a predecessor gate"),
    "status:ready": ("0e8a16", "Self-contained and available to claim"),
    "status:in-progress": ("1d76db", "One agreed owner and agent are working"),
    "status:blocked": ("b60205", "Actual scope, contract or environment blocker recorded"),
    "status:review": ("fbca04", "PR and standalone evidence ready for owner review"),
    "status:done": ("5319e7", "Merged and component acceptance approved"),
    "priority:P0": ("b60205", "MVP priority; does not imply start order"),
    "priority:P1": ("d4c5f9", "Lower priority; independently buildable"),
    "phase:1": ("0052cc", "Sentinel MVP scope"),
    "phase:2": ("bfd4f2", "Optional extension; may be developed independently"),
    "optional": ("c5def5", "Not required for MVP acceptance"),
    **{
        f"lane:{lane}": ("c2e0c6", description)
        for lane, description in {
            "a": "Backend and workflow responsibility lane; not an assignee",
            "b": "Simulation and financial safety lane; not an assignee",
            "c": "Product and language experience lane; not an assignee",
            "d": "Tooling, telemetry and evaluation lane; not an assignee",
        }.items()
    },
}


def index_issues(issues, recorded=None):
    """Find stable task identities including renamed and closed issues; reject conflicts."""
    found = {}
    recorded = recorded or {}
    by_number = {}
    available = {issue["number"] for issue in issues if "pull_request" not in issue}
    for name, reference in recorded.items():
        number = reference["number"]
        if number not in available:
            raise ValueError(f"Recorded {name} issue #{number} is missing; reconcile manually")
        if number in by_number and by_number[number] != name:
            raise ValueError(f"Conflicting recorded identities for issue #{number}")
        by_number[number] = name
    for issue in issues:
        if "pull_request" in issue:
            continue
        title = re.match(r"^\[(SN-\d{3,})\]", issue.get("title", ""))
        marker = re.findall(r"<!-- sentinel-task: (SN-\d{3,}) -->", issue.get("body") or "")
        recorded_name = by_number.get(issue["number"])
        identities = set(
            marker + ([title[1]] if title else []) + ([recorded_name] if recorded_name else [])
        )
        if len(identities) > 1:
            raise ValueError(f"Conflicting task identities on issue #{issue['number']}")
        if not identities:
            continue
        name = identities.pop()
        if name in found and found[name]["number"] != issue["number"]:
            raise ValueError(
                f"Duplicate {name}: issues #{found[name]['number']} and #{issue['number']}"
            )
        found[name] = issue
    return found


def merge_issue_maps(tracked, checkpoint):
    """Recover a partial publication without changing an already recorded identity."""
    result = dict(tracked)
    for name, issue in checkpoint.items():
        if name in result and result[name] != issue:
            raise ValueError(f"{name}: conflicting tracked/checkpoint issue identity")
        result[name] = issue
    return result


def render_issue(task, repository, commit, baseline):
    """Create a self-contained brief with a verified, fully embedded contract baseline."""
    if hashlib.sha256(baseline.encode()).hexdigest() != task["contract_baseline"]["sha256"]:
        raise ValueError(f"{task['id']}: baseline digest mismatch")
    blob = f"https://github.com/{repository}/blob/{commit}"
    lines = [
        f"<!-- sentinel-task: {task['id']} -->",
        f"# {task['id']}: {task['title']}",
        "",
        "## Outcome and independence",
        "",
        *task["scope"],
        "",
        "**No task-completion prerequisites.** Start from the shared baseline "
        "and use local peer stubs. "
        "Do not wait for another issue to finish.",
        "",
        f"- Owned root: `{task['root']}/`",
        f"- Branch: `{task['branch']}`",
        f"- Lane: {task['lane']} (responsibility, not assignment)",
        f"- Phase: {task['phase']}; priority: {task['priority']}; "
        f"optional for MVP: {'yes' if task['optional'] else 'no'}",
        f"- Baseline commit: `{commit}`",
        f"- Contract version: `{task['contract_baseline']['version']}`",
        f"- Contract SHA-256: `{task['contract_baseline']['sha256']}`",
        "",
        "## Read before claiming",
        "",
        f"- [Repository agent rules]({blob}/AGENTS.md) "
        f"and [claim/PR workflow]({blob}/CONTRIBUTING.md)",
        f"- [Owned module guide]({blob}/{task['root']}/README.md) "
        f"and [scoped agent rules]({blob}/{task['root']}/AGENTS.md)",
        f"- [Clean architecture]({blob}/docs/architecture.md) "
        f"and [test evidence rules]({blob}/docs/testing.md)",
        "",
        "## Owned paths",
        "",
        *[f"- `{p}`" for p in task["paths"]],
        "",
        "Keep dependencies, migrations, fixtures, tests, configuration and changelog "
        "inside this root. "
        "Do not edit another task's source, tables, manifest or lockfile.",
        "",
        "## Interfaces and local doubles",
        "",
        f"- Produces: {', '.join('`' + p + '`' for p in task['produces'])}",
        f"- Consumes: {', '.join('`' + p + '`' for p in task['consumes']) or 'None'}",
        "- Optional consumed ports: "
        f"{', '.join('`' + p + '`' for p in task['optional_consumes']) or 'None'}",
        "",
    ]
    for stub in task["standalone"]["peer_stubs"]:
        lines.append(
            f"- `{stub['port']}` stub in `{stub['location']}`: {', '.join(stub['cases'])}."
        )
    lines += [
        "",
        "## Required deliverables",
        "",
        *[f"- [ ] {d}" for d in task["standalone"]["deliverables"]],
        f"- [ ] Update `{task['root']}/CHANGELOG.md` and implementation/setup guidance.",
        "",
        "## Acceptance criteria",
        "",
        *[f"- [ ] {a}" for a in task["acceptance"]],
        "",
        "## Implementation and verification",
        "",
        "1. Claim the issue after rechecking assignees/comments; "
        "record human, agent/session, UTC time and owned worktree.",
        "2. Read the supplied contracts; include the relevant typed snapshots "
        "and deterministic local peers in the owned root.",
        "3. Write meaningful acceptance tests first; confirm the intended failure, "
        "implement the narrow component, and rerun the tests.",
        "4. Provide module-local setup/run commands and the following check target. "
        "It is a deliverable, not an existing passing check:",
        "",
        "```sh",
        task["standalone"]["check_command"],
        "```",
        "",
        task["standalone"]["independence_proof"],
        "",
        "5. Test unavailable/unauthorized/malformed peer behavior "
        "through the real adapter boundary. "
        "Never silently replace real-peer failures with fixture success.",
        "6. Update the module changelog/docs, run repository checks, "
        "and submit a PR targeting main with `Refs #<this issue>`.",
        "",
        "## Evidence and handoff",
        "",
        *[f"- {e}" for e in task["evidence"]],
        "",
        "Progress comment: owner/agent, UTC time, branch + pushed commit/PR, completed, "
        "exact checks/results, actual blocker, next action and next update.",
        "",
        "## Assembly limits",
        "",
        *[f"- {a}" for a in task["assembly_acceptance"]],
        "",
        "Component acceptance closes this task only after owner review and merge. "
        "Product release and external pilot acceptance are separate. "
        "Agents never merge or enable auto-merge.",
        "",
        "<details>",
        "<summary>Complete pinned contract baseline (available without another task)</summary>",
        "",
        baseline,
        "</details>",
        "",
    ]
    result = "\n".join(lines)
    if len(result.encode()) >= 60000:
        raise ValueError(f"{task['id']}: issue body exceeds the conservative size limit")
    return result


def gh_json(arguments, payload=None):
    command = ["gh", "api", *arguments]
    if payload is not None:
        command += ["--input", "-"]
    result = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def write_mapping(path, issues):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({"repository": REPOSITORY, "issues": issues}, indent=2) + "\n")
    temporary.replace(path)


def require_commit_files(root, commit, paths):
    """Never attach a reviewed commit label to different working-tree instructions."""
    for path in sorted(set(paths)):
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"{commit}:{path}"], capture_output=True, check=False
        )
        if result.returncode or result.stdout != (root / path).read_bytes():
            raise ValueError(f"{path} differs from the supplied reviewed commit {commit}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-commit",
        required=True,
        help="Reviewed local baseline commit, published with the initial bootstrap",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Create missing labels/issues; preserve existing issues and assignments",
    )
    parser.add_argument(
        "--initial-status", choices=("status:ready", "status:backlog"), default="status:ready"
    )
    options = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", options.base_commit):
        parser.error("--base-commit must be a full commit SHA")
    errors = validate_repository()
    if errors:
        parser.error("; ".join(errors))
    subprocess.run(
        ["git", "cat-file", "-e", options.base_commit + "^{commit}"],
        check=True,
        capture_output=True,
    )
    tasks = json.loads((REPOSITORY_ROOT / "docs/tasks.json").read_text())
    linked_files = [
        "docs/tasks.json",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "docs/architecture.md",
        "docs/testing.md",
    ]
    for task in tasks:
        linked_files += [
            task["contract_baseline"]["document"],
            task["root"] + "/README.md",
            task["root"] + "/AGENTS.md",
        ]
    require_commit_files(REPOSITORY_ROOT, options.base_commit, linked_files)
    output = REPOSITORY_ROOT / ".artifacts/github-tasks"
    output.mkdir(parents=True, exist_ok=True)
    bodies = {}
    for task in tasks:
        baseline = (REPOSITORY_ROOT / task["contract_baseline"]["document"]).read_text()
        body = render_issue(task, REPOSITORY, options.base_commit, baseline)
        bodies[task["id"]] = body
        (output / (task["id"] + ".md")).write_text(body)
    print(f"Rendered {len(tasks)} self-contained task briefs in .artifacts/github-tasks/")
    if not options.publish:
        return
    issue_map = json.loads((REPOSITORY_ROOT / "docs/task-issues.json").read_text())["issues"]
    checkpoint = output / "publication.json"
    if checkpoint.exists():
        recovery = json.loads(checkpoint.read_text())
        if recovery["repository"] != REPOSITORY:
            raise ValueError("Publication checkpoint belongs to another repository")
        issue_map = merge_issue_maps(issue_map, recovery["issues"])
    known_ids = {task["id"] for task in tasks}
    for name, reference in issue_map.items():
        if (
            name not in known_ids
            or reference["url"] != f"https://github.com/{REPOSITORY}/issues/{reference['number']}"
        ):
            raise ValueError(f"Invalid recorded issue reference: {name}")
    pages = gh_json(["--paginate", "--slurp", f"repos/{REPOSITORY}/issues?state=all&per_page=100"])
    existing = index_issues([issue for page in pages for issue in page], issue_map)
    label_pages = gh_json(["--paginate", "--slurp", f"repos/{REPOSITORY}/labels?per_page=100"])
    labels = {label["name"] for page in label_pages for label in page}
    for name, (color, description) in LABELS.items():
        if name not in labels:
            gh_json(
                ["--method", "POST", f"repos/{REPOSITORY}/labels"],
                {"name": name, "color": color, "description": description},
            )
    for task in tasks:
        name = task["id"]
        issue = existing.get(name)
        if issue is None:
            task_labels = [
                "agents",
                options.initial_status,
                f"lane:{task['lane'].lower()}",
                f"phase:{task['phase']}",
                f"priority:{task['priority']}",
            ]
            if task["optional"]:
                task_labels.append("optional")
            issue = gh_json(
                ["--method", "POST", f"repos/{REPOSITORY}/issues"],
                {
                    "title": f"[{name}] {task['title']}",
                    "body": bodies[name],
                    "labels": task_labels,
                },
            )
            existing[name] = issue
            action = "Created"
        else:
            action = "Preserved existing"
        issue_map[name] = {"number": issue["number"], "url": issue["html_url"]}
        write_mapping(output / "publication.json", issue_map)
        print(f"{action} {name}: {issue['html_url']}", flush=True)
    write_mapping(REPOSITORY_ROOT / "docs/task-issues.json", issue_map)


if __name__ == "__main__":
    main()
