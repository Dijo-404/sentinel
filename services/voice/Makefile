UV ?= uv

.PHONY: setup check preview client
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen sentinel-voice

client: setup
	$(UV) run --frozen sentinel-voice-client
