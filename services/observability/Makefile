UV ?= uv

.PHONY: setup check preview seed
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen sentinel-observability serve

seed: setup
	$(UV) run --frozen sentinel-observability seed
