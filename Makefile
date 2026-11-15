PYTHON ?= python3
UV ?= uv
NPM ?= npm
RUFF := tooling/lint/.venv/bin/ruff
PRETTIER := tooling/lint/node_modules/.bin/prettier

.PHONY: check validate test setup-lint lint format

check: validate test

validate:
	$(PYTHON) -m scripts.repository.validate

test:
	$(PYTHON) -m unittest discover -s tests/repository -v

setup-lint:
	$(UV) venv --python $(PYTHON) --allow-existing tooling/lint/.venv
	$(UV) pip install --python tooling/lint/.venv/bin/python -r tooling/lint/requirements.txt
	$(NPM) ci --prefix tooling/lint --ignore-scripts --no-audit --no-fund

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(PRETTIER) --check .

format:
	$(RUFF) check --fix .
	$(RUFF) format .
	$(PRETTIER) --write .
