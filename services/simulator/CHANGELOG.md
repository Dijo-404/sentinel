# SN-004 changelog

## Unreleased

- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Fixed — payment merchant_ref on transaction wire

- `Payment.to_dict()` includes `merchant_ref`. Journey seeds and default
  `SIMULATOR_MERCHANT_REF` use `merchant-demo-1` (sandbox matrix).

### Added — 14 November 2026 (Refs #79)

- V1 sandbox hardening: `SIMULATOR_MODE=real-peers` for assembly probes while `readyz` keeps `payment_provider=simulator` and `evidence_mode=fixture` (never live).
- Journey seed packs: `pending`, `merchant_mismatch`, `duplicate_payment` (₹1500 / 150000), `refund_pending`; fault schedules `timeout-after-accept`, `duplicate-webhook`, `out-of-order`.
- ProviderAdapter surface docs + `GET /v1/settlements/{provider_ref}` credit alias; signed webhook emit (`SIMULATOR_WEBHOOK_HMAC_KEY` shared with verifier).
- `demo-reset` CLI/admin gated to `SIMULATOR_SANDBOX=true` and tenant `tenant-demo` only.
- Default sandbox tenant `tenant-demo`; admin seed/fault CLI helpers.

### Changed — 14 November 2026

- Canonical tokens `tok-workflow` / `tok-verifier` / `tok-dispatcher` / `tok-sandbox-admin` (legacy `*-demo` aliases kept). Refs #77.

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- Standalone `sentinel-simulator` package: FastAPI `payment-provider.v1` routes, seeded DEMO-ORDER-42 dual-capture fixture, bearer principal map, and in-memory store.
- Deterministic fault controls (outage, delay, timeout-after-accept, duplicate events, out-of-order credit) with inspectable refund stats.
- Separate provider-confirm and credit-confirm admin paths so provider outcome and credit stay distinct events.
- Module `make check` (uv sync, ruff, pytest), `.env.example`, contract snapshot, and demo fixture.

### Implementation status

- Module-local fixture checks cover acceptance criteria and fault/auth boundaries.
- Assembled real-peer product wiring and external pilot settlement remain owner-run / unverified.
