# Changelog

This file tracks coordinated repository/release changes. Each independent module maintains its own changelog to avoid shared-file conflicts.

## Unreleased

### Changed — 14 November 2026

- Rewrote root README around useful money-path / authority / evidence-ladder diagrams; kept V1 sandbox honesty (`provider-sandbox-only`); dropped documentation-only noise from the env table.
- Refreshed root README, architecture, and repository-structure docs for thirty-four implemented modules (SN-001–034), including merchant-ops ports.
- Updated module guides, compatibility notes, embedded pins, and `packages/contract-checks` baseline copy to contract pin `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`, and describe implemented `make check` targets.
- Clarified roadmap: components are on `main`; local MVP wiring, assembled journey evidence, and strict release remain open.

### Added — 13 November 2026

- Sentinel repository structure, clean-architecture guidance, agent coordination rules and claim/PR handoff templates.
- Independently owned component roots with scoped instructions, detailed task guides and local changelogs (originally twenty-six; later extended through SN-034).
- Versioned task contracts, zero-prerequisite task metadata, GitHub publication tooling and an issue register.
- Python-standard-library repository checks and regression tests; pinned-action CI without payment credentials or unfinished services.
- Source Phase 1/Phase 2 specifications and pitch PDF, preserved as supplied.
- Apache License 2.0 at the repository root.

### Changed — 13 November 2026

- Reorganized the root README using the supplied project template, with working setup commands, documentation links, repository CI/license badges, and explicit runtime limits.
- Kept machine-local RTK instructions in agent-global configuration instead of importing an absolute path from repository agent rules.

### Limits

- Assembled multi-service MVP runtime, strict release evidence against real peers, live inference quality, and external pilot acceptance remain separate owner decisions.
- Publication, branch protection and CI observations are recorded in [repository setup evidence](docs/repository-setup.md).
