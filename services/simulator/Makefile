UV ?= uv

.PHONY: setup check preview
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen sentinel-simulator serve --host 127.0.0.1 --port 8094
