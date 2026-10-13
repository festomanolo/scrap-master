# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Changed

- Project renamed to **Scrap Master** (`scrap-master` CLI, `scrap_master` Python package, `~/.scrap-master` config directory, `SCRAP_MASTER_*` environment variables).
- All documentation, CLI output, skill files, scripts and tests are now in English only.
- README rewritten around what the tool does and how to use it.

### Removed

- Third-party sponsor, partner, contact and community sections, localized READMEs and promotional assets.
- Upstream-sync helper script and old design specs.

### Fixed

- Syntax error in the OpenCLI backend hint string that prevented the package from importing.
- Tests asserting on stale non-English messages now assert on the actual English output.
