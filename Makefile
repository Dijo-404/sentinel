PYTHON ?= python3

.PHONY: check validate test

check: validate test

validate:
	$(PYTHON) -m scripts.repository.validate

test:
	$(PYTHON) -m unittest discover -s tests/repository -v
