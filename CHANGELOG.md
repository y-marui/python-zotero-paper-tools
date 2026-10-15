# Changelog

## [Unreleased]

### Added

- Adopted the python-package-template layout: `AI_CONTEXT.md`, `docs/`, `CONTRIBUTING.md`, `SECURITY.md`, issue/PR templates, pre-commit hooks, charter check scripts, and `README-jp.md` as the canonical README.
- Installed dev-charter (full) as a git subtree under `docs/dev-charter/`.
- mypy strict in `make all` and CI; CI now also runs the security scan, build, and the dev-charter check.

### Changed

- Moved tests to `tests/unit/` and `tests/integration/`.
- Added type annotations required by mypy strict.
