UV ?= uv

.PHONY: setup check preview seed flush-workflow
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen uvicorn sentinel_api.bootstrap:app --host 127.0.0.1 --port 8080

# Sandbox-only: ESCALATED + HISTORY cases (messages + audit events) for tenant-demo.
# Requires SENTINEL_V1_SANDBOX=1 (or SENTINEL_API_SANDBOX=1) and SENTINEL_API_DATABASE_URL.
seed: setup
	$(UV) run --frozen sentinel-api seed

# Continuous outbox delivery (reclaims stale CLAIMED leases). Not mutation-only.
flush-workflow: setup
	$(UV) run --frozen sentinel-api flush-workflow --loop --interval 2
