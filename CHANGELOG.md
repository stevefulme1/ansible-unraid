# Changelog

All notable changes to **stevefulme1.unraid** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-05-15

### Added

- Comprehensive unit and integration test suites
- Pre-commit and linting configuration
- Production-ready roles with real module calls
- Limit/offset pagination parameters to all `_info` modules
- Role README.md files for Galaxy import compliance

### Fixed

- Add `document-start` to YAML files
- Resolve DOCUMENTATION structure issues in `notification_info` and `share_info`
- Resolve CI failures across lint, yaml, and unit test tolerance
- Remove broken unit tests
- Add missing role README files
- Resolve Galaxy import validation issues

### Security

- Default to `wss://` for WebSocket connections
- Fix command injection in `vm_snapshot.py`

## [1.2.0] - 2026-05-15

### Added

- 39 read-only info modules for full Unraid API coverage
- 10 Day-2 operation roles (array, disk, docker, flash, monitoring, network, notification, share, user, vm)
- Total: 109 modules, 10 roles, full EDA/inventory coverage

### Fixed

- Bad return value key names
- Missing `no_log` on ssh key parameter
- Mangled text in `certificate.py` documentation
- Typo `provisioneded` to `provisioned` in `certificate.py`
- Update `certificate.py` docs to match renamed state choices
- Sanity findings for new modules

## [1.0.0] - 2026-05-15

### Added

- GraphQL API client for Unraid 7.2+
- 18 core modules: `facts`, `array`, `parity`, `disk`, `share`, `docker_container`, `docker_container_update`, `docker_network`, `vm`, `user`, `api_key`, `notification`, `ups`, `flash_backup`, `settings`, `system`
- `unraid_inventory` dynamic inventory plugin
- `unraid_events` EDA event source plugin
