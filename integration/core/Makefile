UV ?= uv

.PHONY: setup check preview seed-sandbox verify-wave0-1 verify-wave2 verify-wave3 verify-wave4
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
# Wave 0–4 peers run `make seed` when DATABASE_URL env is set; others SKIP.
seed-sandbox: setup
	SENTINEL_V1_SANDBOX=$${SENTINEL_V1_SANDBOX:-1} \
	CORE_ASSEMBLY_TENANT_ID=$${CORE_ASSEMBLY_TENANT_ID:-tenant-demo} \
	$(UV) run --frozen sentinel-core-assembly seed-sandbox

# Live peers must be up + seeded. Fails closed on empty DB / connect error.
verify-wave0-1: setup
	./scripts/verify_wave0_1.sh

# case-api :8080 seeded. Optional VERIFY_IDENTITY_TOKEN for identity :8012 team.
verify-wave2: setup
	./scripts/verify_wave2.sh

# identity :8012 seeded. Session via login or VERIFY_IDENTITY_TOKEN (not tok-*).
verify-wave3: setup
	./scripts/verify_wave3.sh

# assistant :8026, knowledge :8034, ops-activity :8029 seeded; voice :8017 caps;
# offline approval-ui package smoke.
verify-wave4: setup
	./scripts/verify_wave4.sh
