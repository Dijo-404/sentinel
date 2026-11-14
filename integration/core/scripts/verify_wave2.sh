#!/usr/bin/env bash
# Wave 2: assert HTTP 200 + seeded JSON from case-api ops surfaces.
# Requires case-api :8080 up and seeded (make -C apps/api seed).
# Optional: VERIFY_IDENTITY_TOKEN (supervisor session) + identity :8012 for /v1/ops/team.
# Exits nonzero without seed / peers down. No real money.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
if [[ -f .env ]]; then
  set -a
  # demo-only local env; never commit secrets
  source .env
  set +a
fi

echo "verify-wave2: case-api ESCALATED + HISTORY + messages + audit-events (+ optional identity team)"
uv run --frozen sentinel-core-assembly verify-wave2
