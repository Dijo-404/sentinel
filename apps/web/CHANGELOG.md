# SN-012 / SN-038 changelog

## Unreleased

### Added — 14 November 2026

<<<<<<< HEAD
- Supervisor approvals queue + decision workspace (`/supervisor/approvals`, `/supervisor/approvals/[actionId]`) embed local `approval-ui.v1` substitute with exact digest/revision/expiry via case-api `decide` proxy (Refs #100 / M4.2).
- Supervisor case review `/supervisor/cases/[caseId]` with opt-in approval slot; legacy `/ops` evidence keeps approve controls off (`enableApproval` default false).
=======
- Real-peers identity.v1 HTTP client (`createRealPeerIdentityClient`): login/register/me/workspaces select/logout + admin invite/list against `IDENTITY_BASE_URL` (default `http://127.0.0.1:8012`). Fail-closed on missing base URL, network failure, or malformed peer JSON; fixture stub retained for `NEXT_PUBLIC_SHELL_MODE=fixture`. Session token stays in httpOnly cookie — never `NEXT_PUBLIC_*` (Refs #100).
>>>>>>> 95bf520 (feat(web): wire real-peers identity.v1 HTTP client)

### Fixed — 14 November 2026

- Session cookie set only after portal role match; mismatch clears cookie and revokes provisional session. Active assignment bound to requested portal before cookie write (Refs #100 / PR #107).
- `registerCustomerAccount` rejects privileged client fields before identity peer call. Safe redirects normalize path, reject `..`, require exact `/{role}` prefix.
- Legacy `/intake` and `/ops` gated with `requireRole` / `requireAnyRole` (customer; operator|supervisor).

### Added — 14 November 2026

- SN-038 six role portals: `/customer|merchant|operator|supervisor|risk|admin` login + protected dashboards; customer `/register`; shared `RoleLogin`, `ProtectedShell`, unauthorized workspace chooser (Refs #100).
- Admin users directory + invite form wired to `tests/stubs/identity`; `PermissionPreview` advisory only; staff invite rejects `customer` role.
- Server session cookie helpers (`sentinel_session`), fixture identity double, real-peers refuses `NEXT_PUBLIC_*` identity bearers.
- Design tokens: graphite/white surfaces with blue primary (§13.1). Legacy `/intake` and `/ops` kept for compatibility.
- Vitest coverage for identity stub, auth helpers, role-mismatch UI, and no customer staff-register path.

### Fixed — 14 November 2026

- `loadShellConfig` refuses `real-peers` when bearer would come from `NEXT_PUBLIC_DEMO_TOKEN`; requires server-only `CASE_API_BEARER_TOKEN` (`PeerError` `INVALID_CONFIG`). `.env.example` warns never put secrets in `NEXT_PUBLIC_*` (ShellProvider is a client component).

### Added — 14 November 2026

- `GET /v1/capabilities` assembly probe: `{ contract_version, component: "web-shell", port: "web-shell.v1", mode }` from `NEXT_PUBLIC_SHELL_MODE` (Refs #76).

### Changed — 14 November 2026

- `.env.example` uses canonical sandbox tokens/ports (`tok-customer`, case API `:8080`, web `:3012`). Refs #77.

### Added — 13 November 2026

- Next.js web shell (`web-shell.v1`): text intake, case timeline, operator queue, evidence workspace.
- Domain masking for subject/transaction/provider/order refs; exact pending/provider/credit/escalation labels.
- Local stubs for `case-api.v1`, `approval-ui.v1`, `voice.v1` under `tests/stubs/` (valid, unavailable, malformed, unauthorized_or_out_of_scope).
- Real-peer case-api adapter that surfaces failures without fixture fallback.
- Approval and voice component slots with local substitutes; voice disabled by default.
- Module `Makefile` (`make check`), `.env.example`, contract snapshots/fixtures, Vitest browser-state checks.

### Implementation status

- Standalone fixture checks implemented. Assembled SN-007/SN-013/SN-017 real-peer evidence unverified.
- Contract baseline SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
