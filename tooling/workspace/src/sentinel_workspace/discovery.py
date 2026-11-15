"""Filesystem/task-file adapter: validate every declaration before execution."""

import json
import re
from pathlib import Path

from .contracts import Module, ModuleResult


def relative_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(
            not re.fullmatch(r"[A-Za-z0-9_.-]+", part) or part in {".", "..", ".git"}
            for part in value.split("/")
        )
    ):
        raise ValueError("paths must be normalized repository-relative paths")
    return value


def contained(repo: Path, relative: str) -> Path:
    path = repo / relative
    if not path.resolve().is_relative_to(repo):
        raise ValueError("module path or Makefile escapes the repository")
    return path


def load_modules(repo: Path, tasks_file: Path) -> list[Module]:
    with tasks_file.open("rb") as stream:
        data = stream.read(1_048_577)
    if len(data) > 1_048_576:
        raise ValueError("task file exceeds 1 MiB")
    tasks = json.loads(data)
    if not isinstance(tasks, list):
        raise ValueError("task file must contain a list")
    modules: list[Module] = []
    for task in tasks:
        if (
            not isinstance(task, dict)
            or not isinstance(task.get("id"), str)
            or not re.fullmatch(r"SN-[0-9]{3}", task["id"])
        ):
            raise ValueError("each task must have a valid SN-NNN id")
        root = relative_path(task.get("root"))
        path = contained(repo, root)
        contained(repo, root + "/Makefile")
        if path.exists() and not path.is_dir():
            raise ValueError("module root must be a directory")
        resolved = path.resolve()
        if any(
            task["id"] == module.id
            or resolved.is_relative_to((repo / module.root).resolve())
            or (repo / module.root).resolve().is_relative_to(resolved)
            for module in modules
        ):
            raise ValueError("duplicate id or overlapping module roots")
        paths = task.get("paths", [root + "/**"])
        if not isinstance(paths, list):
            raise ValueError("task paths must be a list")
        for owned in paths:
            relative_path(owned[:-3] if isinstance(owned, str) and owned.endswith("/**") else owned)
        standalone = task.get("standalone", {})
        if (
            not isinstance(standalone, dict)
            or standalone.get("check_command", f"make -C {root} check") != f"make -C {root} check"
        ):
            raise ValueError("only the module-local make check command is supported")
        modules.append(Module(task["id"], root, tuple(paths)))
    return modules


def discover(repo: Path, module: Module) -> ModuleResult:
    path = contained(repo, module.root)
    makefile = contained(repo, module.root + "/Makefile")
    status = "ABSENT" if not path.exists() else "READY" if makefile.is_file() else "UNIMPLEMENTED"
    return ModuleResult(module.id, module.root, status)


def selected_by_changes(module: Module, paths: list[str]) -> bool:
    for changed in paths:
        if changed == module.root or changed.startswith(module.root + "/"):
            return True
        for owned in module.paths:
            if changed == owned or (owned.endswith("/**") and changed.startswith(owned[:-2])):
                return True
    return False
