"""CLI composition; JSON goes to stdout and input errors to stderr."""

import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

from .contracts import BASELINE_SHA256, BASELINE_VERSION, CONTRACT_VERSION, FAILURES, ModuleResult
from .discovery import discover, load_modules, selected_by_changes
from .runner import run_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover or check independent declared modules")
    parser.add_argument("command", choices=("discover", "check"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--tasks", type=Path, default=Path("docs/tasks.json"))
    parser.add_argument("--module", action="append", default=[])
    parser.add_argument("--changed-paths", type=Path, help="NUL-separated git diff --name-only output")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--max-output-bytes", type=int, default=65536)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0 or args.max_output_bytes <= 0:
        parser.error("timeout and max-output-bytes must be positive finite values")
    try:
        repo = args.repo.resolve(strict=True)
        if not repo.is_dir():
            raise ValueError("repository must be a directory")
        modules = load_modules(repo, repo / args.tasks)
        if set(args.module) - {module.id for module in modules}:
            raise ValueError("unknown module selection")
        changed = None
        if args.changed_paths:
            changed = [path.decode("utf-8", errors="surrogateescape")
                       for path in args.changed_paths.read_bytes().split(b"\0") if path]
        results = []
        for module in modules:
            selected = (not args.module or module.id in args.module) and (
                changed is None or selected_by_changes(module, changed))
            result = discover(repo, module) if selected else ModuleResult(module.id, module.root, "SKIPPED")
            if args.command == "check" and result.status == "READY":
                result = run_check(repo, module, timeout=args.timeout,
                                   max_output_bytes=args.max_output_bytes)
            results.append(result)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"contract_version": CONTRACT_VERSION,
                      "baseline_version": BASELINE_VERSION, "baseline_sha256": BASELINE_SHA256,
                      "modules": [asdict(result) for result in results]}, indent=2))
    return int(any(result.status in FAILURES for result in results))


if __name__ == "__main__":
    sys.exit(main())
