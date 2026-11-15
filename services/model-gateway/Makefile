UV ?= uv

.PHONY: setup check preview live-test
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen sentinel-model-gateway serve

# Real Sarvam call; needs SARVAM_API_KEY in the environment. Never part of `check`.
live-test: setup
	MODEL_GATEWAY_LIVE_TEST=1 $(UV) run --frozen pytest tests/unit/test_live.py -v
