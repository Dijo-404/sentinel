UV ?= uv

.PHONY: setup check run
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest
	$(UV) run --frozen sentinel-evaluation self-test

run: setup
	$(UV) run --frozen sentinel-evaluation run --candidate conforming --mode fixture
