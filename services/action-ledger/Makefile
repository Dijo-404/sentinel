UV ?= uv

.PHONY: setup check preview migrate
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest

preview: setup
	$(UV) run --frozen uvicorn sentinel_action_ledger.bootstrap:create_preview_app --factory --host 127.0.0.1 --port 8009

migrate: setup
	$(UV) run --frozen alembic -c alembic.ini upgrade head
