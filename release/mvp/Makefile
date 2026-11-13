PYTHON ?= python3

.PHONY: setup check preview self-test
setup:
	uv sync --locked

check: setup
	PYTHONPATH=src:$(CURDIR) $(PYTHON) -m unittest discover -s tests -v
	PYTHONPATH=src:$(CURDIR) $(PYTHON) -m sentinel_release_mvp self-test --json

preview:
	PYTHONPATH=src:$(CURDIR) $(PYTHON) -m sentinel_release_mvp procedure

self-test:
	PYTHONPATH=src:$(CURDIR) $(PYTHON) -m sentinel_release_mvp self-test --json
