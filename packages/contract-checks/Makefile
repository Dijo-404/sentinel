.PHONY: setup check run
setup:
	uv sync --locked

check:
	uv run --locked python -m unittest discover -s tests -v
	uv run --locked sentinel-contracts check

run:
	uv run --locked sentinel-contracts check
