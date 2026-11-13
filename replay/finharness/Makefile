UV ?= uv

.PHONY: setup check preview
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen sentinel-harness-replay compare --fixture bundled/dup_refund_timeout_001
