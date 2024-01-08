# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

The changelog is applicable from version `1.0.0` onwards.

---

## [Unreleased]

### Added

- APPCLI-133: Add fix for Git repository ownership issue to the AppCli Dockerfile.
- APED-67: Add support for running `NullOrchestrator` apps on Windows OS.
- APPCLI-112: Autovalidate config file when a `.schema.json` file is provided.
- APPCLI-115: Enable automerge for dependabot PRs.
- APPCLI-116: Set Ruff as the linter and formatter.
- AF-209: Build the docker-compose plugin into the appcli image.
- DIS-395: Limit the backups to 10 as default.

### Fixed

- APED-37: Prevent quoted arguments with spaces splitting into multiple arguments in the launcher script.

---

## [2.2.0] - 2023-07-14

### Added

- APED-25: Add `NullOrchestrator` to support standalone applications.

---

## [2.1.0] - 2023-06-14

### Added

- AF-97:
    - Support mapping in podman socket.
    - Add `debug shell` command.
    - Add `DEV MODE` to facilitate running/testing outside of docker container.
    - Pass details of calling user into appcli.

---

## [2.0.0] - 2023-05-18

Marked as a major release as `1.4.0` should have been due to breaking changes.

### Fixed

- TERA-1325: Fix incorrect stream printing and class names.

---

## [1.5.0] - 2023-04-19

### Added

- APPCLI-104: Store generated `config` backups in nested `.generated-archive` directory.
- APPCLI-106: Configure and apply on install by default.
- APPCLI-100: Be more explicit when appcli instance fails to start.

### Fixed

- APPCLI-108: Remove the deprecated `distutils` package.
- APPCLI-110: Fix appcli not working with docker-compose >= 2.6.0.

---

## [1.4.0] - 2022-10-10

### Breaking Changes from 1.3.6

- As a result of supporting application-level settings files, all references to settings in template
  files have moved. See the README for details on migration.

### Added

- Disable `CHANGELOG.md` github action enforcement for `dependabot`.
- Run hadolint on every commit with the use of [pre-commit](https://pre-commit.com/).
- Add a CI pipeline check to lint the `Dockerfile` using
  [Hadolint](https://github.com/hadolint/hadolint).
- [#239](https://github.com/brightsparklabs/appcli/issues/239) Support application context files,
  which enables application-specific Jinja2 templating contexts.
- Enable admins and developers to fetch decrypted values of encrypted values in settings.
- Add `quickstart.md` file, a guide on setting up a sample appcli application.
- Add [docker-compose](https://docs.docker.com/engine/reference/commandline/compose/) orchestrator
  commands to `README.md`.
- Update `quickstart.md` to include section about development with a local APPCLI instance.
- [#167](https://github.com/brightsparklabs/appcli/issues/167) Added the service status command,
  which details the current status of the system.
- Setup default values for `seed_app_configuration`, `stack_configuration_file`,
  `baseline_templates_dir`, `configurable_templates_dir` and `orchestrator` in the appcli
  constructor.

### Fixed

- On tag commits, Docker images and python wheels should now be correctly published.
- Update the list of commands used in the `quickstart.md` guide to appropriately reflect the
  required functionality needed to get a sample appcli application running.
- Minor updates to styling in `README.md`

---

## [1.3.6] - 2022-01-24

### Fixed

- Remove automatic UPPERCASING of app_name, which breaks workflows that rely on a stable app_name.

---

## [1.3.5] - 2022-01-21

### Added

- Enable custom commands to run `exec` commands on service containers via the orchestrator
- Allow tasks to be run in detached mode with flag `-d/--detach`.
- Renaming the launcher script to create only 1 hidden file:
  `.<timestamp>_<app_name>_<app_version>`.
- [#118](https://github.com/brightsparklabs/appcli/issues/118) Added `version` command to fetch
  version of app managed by appcli.
- [#144](https://github.com/brightsparklabs/appcli/issues/144) Added `--lines/-n` option to the
  `logs` commands for orchestrators. This is the `n` number of lines from the end to start the tail.
- [#147](https://github.com/brightsparklabs/appcli/issues/147) Remove ':' character from backup
  filenames, to allow tools like `tar` to work more easily with the unmodified filename.
- [#165](https://github.com/brightsparklabs/appcli/issues/165) Added ability to
  start/shutdown/restart multiple services at a time with the `service` command.

### Fixed

- Adjust logging header formatting misalignment
- Fixed issue where applications with non-shell-safe `app_name` weren't able to be installed or run.
- Fix Dockerfile issues identified by [Hadolint](https://github.com/hadolint/hadolint).
- Minor fix to README example python script.

---

## [1.3.4] - 2021-05-14

### Fixed

- Stack settings file is no longer overwritten to the default when running `migrate` command.
- [#130](https://github.com/brightsparklabs/appcli/issues/130) Added back in `docker` binary to the
  appcli Docker image, so tasks can now be run again.
- [#115](https://github.com/brightsparklabs/appcli/issues/115) Fixed DockerSwarm orchestrator with
  the addition of the `docker` binary.

---

## [1.3.3] - 2021-05-07

### Added

- [#100](https://github.com/brightsparklabs/appcli/issues/100) Now publishing python wheel to PyPI!

---

## [1.3.2] - 2021-05-06

### Added

- [#128](https://github.com/brightsparklabs/appcli/pull/128) Added `frequency` to individual remote
  backup configurations.

### Fixed

- Fixed [#89](https://github.com/brightsparklabs/appcli/issues/89): `configure get` on a boolean
  returns `None` if setting is `false`.

---

## [1.3.1] - 2021-03-18

### Added

- `install` command script automatically does upgrade if installing over an existing application.

---

## [1.3.0] - 2021-03-17

### Added

- Added `service restart` command to restart service(s) with option `--apply`.
- Backup configuration now supports multiple backup definitions with their own granularity and
  remotes.
- Backup and restore now have options to enable/disable pre-stop/pre-start services.
- Added `--encrypt` option to `configure set` to set an encrypted value directly.
- Value for `configure set` is now optional, and will be interactively requested if missing.
- Various dependency updates.

---

## [1.2.0] - 2021-02-18

### Breaking Changes from 1.1

Appcli no longer exposes internal classes and methods via the root module. To access these classes
and methods, any python referring to the library will need to use full module path references.

### Fixed

- Fixed module imports which were broken due to using `__init__.py`, swapped to using implicit
  namespace modules.

---

## [1.1.3] - 2021-02-17 [BROKEN - DO NOT USE THIS VERSION]

### Added

- `backup` and `restore` commands and its associated configuration.

---

## [1.1.2] - 2021-02-10 [BROKEN - DO NOT USE THIS VERSION]

### Added

- The launcher now supports `NO_INTERACTIVE` environment variable to disable interactive mode.
- Expose the `APP_NAME` environment variable to the launcher container.

### Fixed

- Fixed issue where `migrate` command couldn't be run when the application needed to be migrated.

---

## [1.1.1] - 2020-11-26

### Added

- Added TravisCI build status badge to the README.

### Fixed

- Fixed failing linting in `1.1.0`.

---

## [1.1.0] - 2020-11-26

### Added

- [#33](https://github.com/brightsparklabs/appcli/issues/33) Added support for 'tasks', and renamed
  existing capability to 'services'.
- [#20](https://github.com/brightsparklabs/appcli/issues/20) Added ability to specify docker-compose
  override directories for services and tasks.
- [#32](https://github.com/brightsparklabs/appcli/issues/32) Added ability to disable `--tty` when
  using launcher script.
- [#37](https://github.com/brightsparklabs/appcli/issues/37) Added `configure edit` command to open
  settings file in `vim-tiny`.
- [#56](https://github.com/brightsparklabs/appcli/issues/56) Allow `service start` and `service
  shutdown` to stop individual services for docker-compose orchestrator.
- [#23](https://github.com/brightsparklabs/appcli/issues/23) Allow `configure set` to specify type
  of value. Supports str, int, float, and bool.
- [#36](https://github.com/brightsparklabs/appcli/issues/36) Added `service shutdown` command as an
  alias of `service stop`.
- [#35](https://github.com/brightsparklabs/appcli/issues/35) Added `upgrade` command as an alias of
  `migrate`.
- Added hidden `debug info` command to print out some debugging information about the current
  application and appcli configuration.

### Changed

- [#49](https://github.com/brightsparklabs/appcli/issues/49) Log messages now include timezone.
- [#26](https://github.com/brightsparklabs/appcli/issues/26) Various enhancements to the README.

[Commits](https://github.com/brightsparklabs/appcli/compare/1.0.1...1.1.0)

---

## [1.0.1] - 2020-10-08

### Added

- Add option to allow insecure SSL connections during Keycloak initialisation with `init keycloak`
  command.

[Commits](https://github.com/brightsparklabs/appcli/compare/1.0.0...1.0.1)

---

## [1.0.0] - 2020-10-07

_No changelog for this release._
