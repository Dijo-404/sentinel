"""Artifact digest and timestamp integrity checks."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sentinel_release_mvp.contracts import CheckResult, ComponentEvidence

_RFC3339_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def timestamp_ok(value: str) -> bool:
    return bool(_RFC3339_Z.match(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def check_component_integrity(
    component: ComponentEvidence, *, artifact_root: Path | None = None
) -> CheckResult:
    name = f"integrity:{component.port}"
    if not timestamp_ok(component.observed_at):
        return CheckResult(name, "FAIL", "INVALID_TIMESTAMP")
    if artifact_root is None:
        return CheckResult(name, "PASS", "TIMESTAMP_OK")
    uri = component.artifact_uri
    if uri.startswith("file://"):
        rel = uri.removeprefix("file://")
        path = (artifact_root / rel).resolve()
        try:
            path.relative_to(artifact_root.resolve())
        except ValueError:
            return CheckResult(name, "FAIL", "ARTIFACT_PATH_ESCAPE")
        if not path.is_file():
            return CheckResult(name, "FAIL", "ARTIFACT_MISSING")
        actual = sha256_file(path)
        if actual != component.artifact_digest:
            return CheckResult(name, "FAIL", "ARTIFACT_DIGEST_MISMATCH")
        return CheckResult(name, "PASS", "ARTIFACT_DIGEST_OK")
    # Non-file URIs: digest is still required; content verification deferred.
    return CheckResult(name, "PASS", "DIGEST_DECLARED")
