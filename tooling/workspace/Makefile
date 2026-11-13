PYTHON ?= python3

.PHONY: setup check preview
setup:
	uv sync --locked

check:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

preview:
	PYTHONPATH=src $(PYTHON) -m sentinel_workspace discover --repo tests/fixtures/mini-repo
