# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

The changelog is applicable from version `1.0.0` onwards.

---

## [Unreleased]

---

## [1.3.1] - (18/03/2021)

### Added

- `install` command script automatically does upgrade if installing over an existing application.

## [1.3.0] - (17/03/2021)

### Added

- Added `service restart` command to restart service(s) with option `--apply`.
- Backup configuration now supports multiple backup definitions with their own granularity and remotes.
- Backup and restore now have options to enable/disable pre-stop/pre-start services.
- Added `--encrypt` option to `configure set` to set an encrypted value directly.
- Value for `configure set` is now optional, and will be interactively requested if missing.
- Various dependency updates.

## [1.2.0] - (18/02/2021)

### Breaking Changes from 1.1

Appcli no longer exposes internal classes and methods via the root module. To access these classes and methods,
any python referring to the library will need to use full module path references.

### Fixed

- Fixed module imports which were broken due to using `__init__.py`, swapped to using implicit namespace modules.

## [1.1.3] - (17/02/2021) [BROKEN - DO NOT USE THIS VERSION]

### Added

- `backup` and `restore` commands and its associated configuration.

---
## [1.1.2] - (10/02/2021) [BROKEN - DO NOT USE THIS VERSION]

### Added

- The launcher now supports `NO_INTERACTIVE` environment variable to disable interactive mode.
- Expose the `APP_NAME` environment variable to the launcher container

### Fixed

- Fixed issue where `migrate` command couldn't be run when the application needed to be migrated.

---
## [1.1.1] - (26/11/2020)

### Added

- Added TravisCI build status badge to the README.

### Fixed

- Fixed failing linting in `1.1.0`.

---

## [1.1.0] - (26/11/2020)

### Added

- [#33](https://github.com/brightsparklabs/appcli/issues/33) Added support for 'tasks', and renamed existing capability to 'services'.
- [#20](https://github.com/brightsparklabs/appcli/issues/20) Added ability to specify docker-compose override directories for services and tasks.
- [#32](https://github.com/brightsparklabs/appcli/issues/32) Added ability to disable `--tty` when using launcher script.
- [#37](https://github.com/brightsparklabs/appcli/issues/37) Added `configure edit` command to open settings file in `vim-tiny`.
- [#56](https://github.com/brightsparklabs/appcli/issues/56) Allow `service start` and `service shutdown` to stop individual services for docker-compose orchestrator.
- [#23](https://github.com/brightsparklabs/appcli/issues/23) Allow `configure set` to specify type of value. Supports str, int, float, and bool.
- [#36](https://github.com/brightsparklabs/appcli/issues/36) Added `service shutdown` command as an alias of `service stop`.
- [#35](https://github.com/brightsparklabs/appcli/issues/35) Added `upgrade` command as an alias of `migrate`.
- Added hidden `debug info` command to print out some debugging information about the current application and appcli configuration.

### Changed

- [#49](https://github.com/brightsparklabs/appcli/issues/49) Log messages now include timezone.
- [#26](https://github.com/brightsparklabs/appcli/issues/26) Various enhancements to the README.

[Commits](https://github.com/brightsparklabs/appcli/compare/1.0.1...1.1.0)

---

## [1.0.1] - (08/10/2020)

### Added

- Add option to allow insecure SSL connections during Keycloak initialisation with `init keycloak` command.

[Commits](https://github.com/brightsparklabs/appcli/compare/1.0.0...1.0.1)

---

## [1.0.0] - (07/10/2020)

*No changelog for this release.*
