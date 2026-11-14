#!/usr/bin/env bash
# Fixture RBAC probes (path=rbac-fixture). Exits nonzero on failure.
# Does NOT claim sn009_authority_exercised or full money path.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "sentinel-core-assembly rbac-fixture probes (AUTH-01/invite/AUTH-06)"
uv run --frozen pytest tests/test_rbac_fixture.py -q
