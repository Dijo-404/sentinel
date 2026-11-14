#!/usr/bin/env bash
# Wave 0–1: assert HTTP 200 + seeded JSON from DB-backed peers.
# Requires analytics :8032, disputes :8030, risk :8013 up and seeded.
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

echo "verify-wave0-1: merchant-analytics metrics + disputes list + risk investigations"
uv run --frozen sentinel-core-assembly verify-wave0-1
