UV ?= uv

.PHONY: setup check preview seed
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen sentinel-merchant-teams serve

# Requires MERCHANT_TEAMS_DATABASE_URL (PostgreSQL). Seeds tenant-demo / merchant-demo-1.
seed: setup
	$(UV) run --frozen sentinel-merchant-teams seed
