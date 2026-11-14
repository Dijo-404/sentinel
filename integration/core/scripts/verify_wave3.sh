#!/usr/bin/env bash
# Wave 3: assert HTTP 200 + seeded JSON from identity me/notifications/workspaces;
# forgot returns 202 without email enumeration.
# Requires identity :8012 up and seeded (make -C services/identity seed, or fixture seed on serve).
# Session: VERIFY_IDENTITY_TOKEN or login customer@example.test + IDENTITY_DEMO_PASSWORD.
# Never matrix tok-*. Exits nonzero without seed / peers down. No real money.
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

echo "verify-wave3: identity me + notifications + workspaces + forgot(202 no enum)"
uv run --frozen sentinel-core-assembly verify-wave3
