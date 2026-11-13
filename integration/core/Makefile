UV ?= uv

.PHONY: setup check preview
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest
	$(UV) run --frozen sentinel-core-assembly check

preview: setup
	$(UV) run --frozen sentinel-core-assembly run --mode fixture
