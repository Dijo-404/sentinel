UV ?= uv

.PHONY: setup check preview flush-workflow
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen uvicorn sentinel_api.bootstrap:app --host 127.0.0.1 --port 8080

# Continuous outbox delivery (reclaims stale CLAIMED leases). Not mutation-only.
flush-workflow: setup
	$(UV) run --frozen sentinel-api flush-workflow --loop --interval 2
