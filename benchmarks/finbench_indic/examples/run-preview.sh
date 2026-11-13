#!/usr/bin/env sh
# Fixture preview only. No live peers or payment credentials.
set -eu
cd "$(dirname "$0")/.."
uv run --frozen sentinel-finbench run --dataset indic-fin-v0.1.0 --split val --mode recorded
