#!/usr/bin/env bash
# Wave 6: portal stub inventory empty, fixture assembly honesty labels,
# approval-ui ApprovalPanel package + real-peers slot smoke.
# Default is credential-free (no live peers). Optional:
#   VERIFY_WAVE6_LIVE=1  → real-peers provider subset when peers up
#                          (payment_provider=simulator; see sandbox-runbook).
# Exits nonzero on stub hits / fixture FAIL / missing ApprovalPanel.
# Never claims MVP release. No real money.
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

echo "verify-wave6: stub scan + fixture honesty + approval-ui smoke"
uv run --frozen sentinel-core-assembly verify-wave6
