UV ?= uv

.PHONY: setup check preview
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen sentinel-finbench run --dataset indic-fin-v0.1.0 --split val --mode recorded
