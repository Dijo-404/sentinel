"""Validate the repository baseline without installing application dependencies."""

from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {
    "id", "title", "lane", "phase", "priority", "optional", "branch", "root",
    "depends_on", "paths", "contract_baseline", "produces", "consumes",
    "optional_consumes", "scope", "standalone", "acceptance", "evidence",
    "assembly_acceptance", "gate",
}

# Dependency/build trees are not repository-owned; skip even when names lack a leading dot.
IGNORED_MARKDOWN_DIRS = frozenset({
    "node_modules", "dist", "build", "coverage", "htmlcov", "vendor",
    "venv", "__pycache__",
})


def is_ignored_markdown_path(relative):
    """Return True when a Markdown path lives under a non-owned tree."""
    return any(
        part.startswith(".") or part in IGNORED_MARKDOWN_DIRS
        for part in PurePosixPath(relative).parts
    )


def validate_tasks(tasks, root):
    """Return actionable errors for unsafe ownership or coupled task metadata."""
    errors = []
    if not isinstance(tasks, list) or not tasks:
        return ["Task plan must be a nonempty list"]
    if any(not isinstance(t, dict) or not REQUIRED <= t.keys() for t in tasks):
        return ["Each task must contain all required metadata fields"]
    for field, label in (("id", "task"), ("branch", "branch")):
        for value, count in Counter(t[field] for t in tasks).items():
            if count > 1:
                errors.append(f"duplicate {label}: {value}")
    producers = {}
    owned = []
    for task in tasks:
        name = task["id"]
        if not re.fullmatch(r"SN-\d{3,}", name):
            errors.append(f"{name}: invalid task ID")
        if not re.fullmatch(r"feat/sn-\d{3,}-[a-z0-9-]+", task["branch"]):
            errors.append(f"{name}: invalid feature branch")
        if task["depends_on"]:
            errors.append(f"{name}: task-completion prerequisite is forbidden")
        module_root = task["root"]
        if not re.fullmatch(r"[a-z0-9_-]+(?:/[a-z0-9_-]+)+", module_root):
            errors.append(f"{name}: invalid module root")
        if module_root + "/**" not in task["paths"]:
            errors.append(f"{name}: module root missing from owned paths")
        for path in task["paths"]:
            allowed = path == module_root + "/**" or (
                name == "SN-001" and path == ".github/workflows/module-checks.yml"
            )
            if not allowed:
                errors.append(f"{name}: unexpected owned path {path}")
            owned.append((name, PurePosixPath(path.removesuffix("/**"))))
        baseline = task["contract_baseline"]
        document = root / baseline["document"]
        if not document.resolve().is_relative_to(root.resolve()):
            errors.append(f"{name}: contract path escapes repository")
        elif not document.is_file():
            errors.append(f"{name}: contract path does not exist")
        elif hashlib.sha256(document.read_bytes()).hexdigest() != baseline["sha256"]:
            errors.append(f"{name}: stale contract digest")
        if baseline["version"] != "sentinel.task-contracts.v1":
            errors.append(f"{name}: unsupported contract baseline version")
        for field in ("scope", "acceptance", "evidence", "assembly_acceptance", "produces"):
            if not task[field]:
                errors.append(f"{name}: empty {field}")
        standalone = task["standalone"]
        if standalone.get("check_command") != f"make -C {module_root} check":
            errors.append(f"{name}: standalone check must be module-local")
        if {s["port"] for s in standalone.get("peer_stubs", [])} != set(task["consumes"]):
            errors.append(f"{name}: consumed interface lacks matching peer stub")
        if not set(task["optional_consumes"]) <= set(task["consumes"]):
            errors.append(f"{name}: optional interfaces are not consumed interfaces")
        for port in task["produces"]:
            if port in producers:
                errors.append(f"{name}: duplicate interface producer {port}")
            producers[port] = task
    for index, (first, a) in enumerate(owned):
        for second, b in owned[index + 1:]:
            if first != second and (a == b or a in b.parents or b in a.parents):
                errors.append(f"ownership overlap: {first} {a}, {second} {b}")
    for task in tasks:
        for port in task["consumes"]:
            peer = producers.get(port)
            if peer is None:
                errors.append(f"{task['id']}: unknown consumed interface {port}")
            elif task["phase"] == 1 and not task["optional"] and port not in task["optional_consumes"]:
                if peer["phase"] != 1 or peer["optional"]:
                    errors.append(f"{task['id']}: hidden optional MVP dependency {port}")
    return errors


def valid_markdown_whitespace(text):
    """Allow intentional two-space Markdown hard breaks without rewriting source specs."""
    return text.endswith("\n") and all(
        line[len(line.rstrip()):] in ("", "  ") for line in text.splitlines()
    )


def validate_repository(root=REPOSITORY_ROOT):
    """Check task metadata, documentation, module guides and published references."""
    errors = []
    try:
        tasks = json.loads((root / "docs/tasks.json").read_text())
        errors.extend(validate_tasks(tasks, root))
        if errors:
            return errors
        mapping = json.loads((root / "docs/task-issues.json").read_text())
        if mapping["repository"] != "Dijo-404/sentinel":
            errors.append("Issue map points to a different repository")
        task_ids = {t["id"] for t in tasks}
        if not mapping["issues"].keys() <= task_ids:
            errors.append("Issue map contains unknown task IDs")
        numbers = []
        for name, issue in mapping["issues"].items():
            number = issue["number"]
            if not isinstance(number, int) or number < 1:
                errors.append(f"{name}: invalid issue number")
            if issue["url"] != f"https://github.com/Dijo-404/sentinel/issues/{number}":
                errors.append(f"{name}: issue URL does not match its number")
            numbers.append(number)
        if len(numbers) != len(set(numbers)):
            errors.append("Several tasks map to the same issue")
        register = (root / "docs/task-register.md").read_text()
        if re.findall(r"^\| (SN-\d{3,}) \|", register, re.M) != [t["id"] for t in tasks]:
            errors.append("Task register does not cover the ordered task plan")
        for issue in mapping["issues"].values():
            if issue["url"] not in register:
                errors.append(f"Task register lacks {issue['url']}")
        for task in tasks:
            for name in ("README.md", "AGENTS.md", "CHANGELOG.md"):
                file = root / task["root"] / name
                if not file.is_file() or task["id"] not in file.read_text():
                    errors.append(f"{task['id']}: missing task-scoped {name}")
        for file in root.rglob("*.md"):
            if is_ignored_markdown_path(file.relative_to(root)):
                continue
            text = file.read_text()
            if not valid_markdown_whitespace(text):
                errors.append(f"{file.relative_to(root)}: trailing whitespace or missing final newline")
            # Ignore code examples: paths in templates are illustrative, not links.
            prose = re.sub(r"```.*?```", "", text, flags=re.S)
            for target in re.findall(r"\]\(([^)]+)\)", prose):
                target = target.strip("<>").split("#", 1)[0]
                if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                    continue
                path = (file.parent / unquote(target)).resolve()
                if not path.is_relative_to(root.resolve()) or not path.exists():
                    errors.append(f"{file.relative_to(root)}: invalid local link {target}")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors.append(f"Invalid repository metadata: {exc}")
    return errors


def main():
    errors = validate_repository()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Repository checks passed: independent tasks, owned roots, contracts, issue references and documentation.")
    print("This validates repository metadata; application/component tests are separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
