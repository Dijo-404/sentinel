#!/usr/bin/env bash
# Wave 4: assert HTTP 200 + seeded JSON from assistant/knowledge/ops-activity;
# voice /v1/capabilities; offline approval-ui package export smoke.
# Requires peers up + seeded (make -C integration/core seed-sandbox when DB URLs set).
# Defaults: assistant :8026, knowledge :8034, ops-activity :8029, voice :8017.
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

echo "verify-wave4: assistant/knowledge/ops-activity health+list + voice caps + approval-ui smoke"
uv run --frozen sentinel-core-assembly verify-wave4
