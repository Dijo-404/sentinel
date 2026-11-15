#!/usr/bin/env bash
# Wave 5: assert HTTP 200 + seeded JSON from identity admin roles/tenants,
# policy policies, merchant-teams admin merchants, platform-ai config/integrations,
# evals reports, observability signals.
# Requires peers up + seeded (make -C integration/core seed-sandbox when DB URLs set).
# Defaults: identity :8012, policy :8005, merchant-teams :8034, platform-ai :8036,
# evals :8031, observability :8033.
# Tokens: identity session (admin login); policy tok-platform-admin;
# merchant-teams platform-admin-token; platform-ai/evals/obs admin-token.
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

echo "verify-wave5: identity admin + policy + merchants + platform-ai + evals + obs"
uv run --frozen sentinel-core-assembly verify-wave5
