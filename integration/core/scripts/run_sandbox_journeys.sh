#!/usr/bin/env bash
# Live V1 sandbox assembly. Exits nonzero on failure.
# Default: provider journeys (path=provider-sandbox-only).
# SENTINEL_V1_AUTHORITY_PATH=1 also runs browser_to_credit + duplicate_approval_deny.
# Requires peers up per docs/sandbox-runbook.md. No real money.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export CORE_ASSEMBLY_MODE=real-peers
# shellcheck disable=SC1091
if [[ -f .env ]]; then
  set -a
  # demo-only local env; never commit secrets
  source .env
  set +a
fi

DIGEST="$(printf '0%.0s' {1..64})"
ARTIFACT="sandbox-stack,local://v1-sandbox,${DIGEST},0.1.0,real-component"

echo "sentinel-core-assembly real-peers journeys (payment_provider=simulator)"
uv run --frozen sentinel-core-assembly run --mode real-peers \
  --run-id "sandbox-journeys-$(date -u +%Y%m%dT%H%M%SZ)" \
  --artifact "$ARTIFACT"
