"""Run trusted local Makefiles using argv, with process/output bounds."""

import os
import selectors
import signal
import subprocess
import time
from pathlib import Path

from .contracts import Module, ModuleResult
from .discovery import contained


def run_check(
    repo: Path,
    module: Module,
    *,
    make: str = "make",
    timeout: float = 300,
    max_output_bytes: int = 65536,
) -> ModuleResult:
    root = contained(repo, module.root)
    contained(repo, module.root + "/Makefile")
    try:
        process = subprocess.Popen(
            [make, "--no-print-directory", "-C", str(root), "check"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except OSError:
        return ModuleResult(module.id, module.root, "ERROR", output="unable to start make")

    output = bytearray()
    deadline = time.monotonic() + timeout
    status = None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    status = "TIMEOUT"
                    break
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fd, 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    room = max_output_bytes - len(output)
                    output.extend(chunk[:room])
                    if len(chunk) > room:
                        status = "OUTPUT_LIMIT"
                        break
                if status:
                    break
        if not status:
            try:
                process.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                status = "TIMEOUT"
    finally:
        # Kill the process group, including check children, on a bound violation.
        if status:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        process.stdout.close()
    return ModuleResult(
        module.id,
        module.root,
        status or ("PASS" if process.returncode == 0 else "FAIL"),
        process.returncode,
        output.decode("utf-8", errors="replace"),
    )
