# Repository lint and formatting

Requires Python 3.11+, uv, Node.js 20+, npm, and GNU Make. Run from the repository root:

```sh
make setup-lint  # Install Ruff 0.17.5 and Prettier 3.10.1.
make lint        # Check Python lint, Python formatting, and Prettier formatting.
make format      # Apply safe Ruff fixes, then format all supported files.
make check       # Run the separate repository metadata/tool tests.
```

Ruff lives in `tooling/lint/.venv`; Prettier lives in `tooling/lint/node_modules`.
Their versions are pinned in `requirements.txt` and `package.json`/`package-lock.json`.
No global install, root application manifest, shared application lockfile, or sibling module install is required.
`PYTHON`, `UV`, and `NPM` can override the setup executables.

Root `ruff.toml` sets Python 3.11, a 100-character line limit, and the existing module rule families:
pycodestyle (`E`), Pyflakes (`F`), import sorting (`I`), bugbear (`B`), and pyupgrade (`UP`).
Ruff discovers each module's existing configuration; local rules and module checks remain authoritative.
Prettier handles JavaScript, TypeScript, JSX/TSX, CSS, JSON, YAML, HTML, and Markdown with a 100-character print width.
Markdown prose keeps its existing wrapping. See [Ruff configuration](https://docs.astral.sh/ruff/configuration/)
and [Prettier installation](https://prettier.io/docs/install).

Both tools skip generated dependencies, environments, build output, and worktrees.
Supplied Phase 1/2 specifications and the pinned independent-task contract remain byte-for-byte intact.
Prettier also skips module contract snapshots, fixtures, contract-check data, and package-manager lockfiles;
those files may carry canonical bytes, hashes, or deliberately malformed inputs.
These exclusions live in root `ruff.toml` and `.prettierignore`; application source and tests remain checked.

The repository workflow runs `make lint` independently of root `make check`.
Module-local `make check` still proves the module's tested behavior; lint alone does not prove runtime or payment safety.
