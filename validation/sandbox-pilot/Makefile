UV ?= uv

.PHONY: setup check preview
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest
	$(UV) run --frozen sentinel-sandbox-pilot check

preview: setup
	$(UV) run --frozen sentinel-sandbox-pilot run --mode fixture
