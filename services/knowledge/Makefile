UV ?= uv

.PHONY: setup check preview seed reindex
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen sentinel-knowledge serve

seed: setup
	$(UV) run --frozen sentinel-knowledge seed

reindex: setup
	$(UV) run --frozen sentinel-knowledge reindex
