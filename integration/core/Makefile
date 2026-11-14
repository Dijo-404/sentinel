UV ?= uv

.PHONY: setup check preview seed-sandbox
setup:
	$(UV) sync --frozen

check: setup
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(UV) run --frozen pytest
	$(UV) run --frozen sentinel-core-assembly check

preview: setup
	$(UV) run --frozen sentinel-core-assembly run --mode fixture

# Requires CORE_ASSEMBLY_TENANT_ID=tenant-demo and SENTINEL_V1_SANDBOX=1.
# Peer hooks may SKIP until module make seed lands (wave tasks).
seed-sandbox: setup
	SENTINEL_V1_SANDBOX=$${SENTINEL_V1_SANDBOX:-1} \
	CORE_ASSEMBLY_TENANT_ID=$${CORE_ASSEMBLY_TENANT_ID:-tenant-demo} \
	$(UV) run --frozen sentinel-core-assembly seed-sandbox
