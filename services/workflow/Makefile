UV ?= uv

.PHONY: setup check preview migrate

setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen sentinel-workflow serve

migrate: setup
	$(UV) run --frozen sentinel-workflow migrate
