# BSL Application CLI Library

[![PyPI version](https://badge.fury.io/py/bsl-appcli.svg)](https://badge.fury.io/py/bsl-appcli)
![Test Python](https://github.com/brightsparklabs/appcli/actions/workflows/build_python.yml/badge.svg)

A library for adding CLI interfaces to applications in the brightSPARK Labs style.

## Overview

This library can be leveraged to add a standardised CLI capability to applications to:

- Handle system lifecycle events for services (`service [start|shutdown]`).
- Allow running arbitrary short-lived tasks (`task run`).
- Manage configuration (`configure`).
- Upgrade to a newer version of the application (`upgrade|migrate`).
- And more.

The CLI is designed to run within a Docker container and launch other Docker containers (i.e.
Docker-in-Docker). This is generally managed via a `docker-compose.yml` file.

The library exposes the following environment variables to the `docker-compose.yml` file:

- `APP_VERSION` - the version of containers to launch.
- `<APP_NAME>_CONFIG_DIR` - the directory containing configuration files.
- `<APP_NAME>_DATA_DIR` - the directory containing data produced/consumed by the system.
- `<APP_NAME>_GENERATED_CONFIG_DIR` - the directory containing configuration files generated from
  the templates in `<APP_NAME>_CONFIG_DIR`.
- `<APP_NAME>_BACKUP_DIR` - the directory to use for system backups.
- `<APP_NAME>_ENVIRONMENT` - the deployment environment the system is running in. For example
  `production` or `staging`. This allows multiple instances of the application to run on the same
  Docker daemon. Defaults to `production`.

NOTE:
The `APP_NAME` variable is derived from the `app_name` passed in to the `Configuration` object in
the main python entrypoint to the application. In order for the application to work, the `app_name`
is forced to conform with the shell variable name standard: `[a-zA-Z_][a-zA-Z_0-9]*`. Any characters
that do not fit this regex will be replaced with `_`. See
[here](https://unix.stackexchange.com/questions/428880/list-of-acceptable-initial-characters-for-a-bash-variable)
or [here](https://linuxhint.com/bash-variable-name-rules-legal-illegal/) for details.

The `docker-compose.yml` can be templated by renaming to `docker-compose.yml.j2`, and setting
variables within the `settings.yml` file as described in the Installation section.

Stack variables can be set within the `stack-settings.yml` file as described in the
`Build configuration template directories` section.

## Quick Start

Refer to the [quick start guide](quickstart.md) to get a basic application running.

Otherwise refer to the Installation section below to see all options.

## Installation

### Add the library to your python CLI application

    pip install git+https://github.com/brightsparklabs/appcli.git@<VERSION>

### Define the CLI for your application `myapp`

_Note for appcli version 1.1.3 and below_: Import paths to access to appcli
internal classes and methods is now by a full path, rather than being exposed
at the root. This was done to allow access to all methods and classes using
python3 implicit namespaced packages.

```python
    # filename: myapp.py

    #!/usr/bin/env python3
    # # -*- coding: utf-8 -*-

    # standard libraries
    from pathlib import Path

    # vendor libraries
    from appcli.cli_builder import create_cli
    from appcli.models.configuration import Configuration
    from appcli.orchestrators import DockerComposeOrchestrator

    # ------------------------------------------------------------------------------
    # CONSTANTS
    # ------------------------------------------------------------------------------

    # directory containing this script
    BASE_DIR = Path(__file__).parent

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def main():
        configuration = Configuration(
            app_name='myapp',
            docker_image='brightsparklabs/myapp',
            seed_app_configuration_file=BASE_DIR / 'resources/settings.yml',
            application_context_files_dir=BASE_DIR / 'resources/templates/appcli/context',
            stack_configuration_file=BASE_DIR / 'resources/stack-settings.yml',
            baseline_templates_dir=BASE_DIR / 'resources/templates/baseline',
            configurable_templates_dir=BASE_DIR / 'resources/templates/configurable',
            orchestrator=DockerComposeOrchestrator(
                # NOTE: These paths are relative to 'resources/templates/baseline'.
                docker_compose_file = Path('docker-compose.yml'),
                docker_compose_override_directory = Path('docker-compose.override.d/'),
                docker_compose_task_file = Path('docker-compose.tasks.yml'),
                docker_compose_task_override_directory = Path( 'docker-compose.tasks.override.d/'),
            ),
            mandatory_additional_data_dirs=['EXTRA_DATA',],
            mandatory_additional_env_variables=['ENV_VAR_2',],
        )
        cli = create_cli(configuration)
        cli()

    # ------------------------------------------------------------------------------
    # ENTRYPOINT
    # ------------------------------------------------------------------------------

    if __name__ == '__main__':
        main()
```

A lot of the fields in the appcli constructor can be defaulted, resulting in less code.

```python
configuration = Configuration(
    app_name='myapp',
    docker_image='brightsparklabs/myapp',
)
cli = create_cli(configuration)
cli()
```

#### NullOrchestrator

For applications with no services to orchestrate, the `NullOrchestrator` can be used. This is useful
for appcli applications which consist only of the launcher container containing various additional CLI 
command groups. The `NullOrchestrator` disables commands related to managing services.

```python
orchestrator=NullOrchestrator()
```

#### Custom Commands

You can specify some custom top-level commands by adding click commands or command groups to the
configuration object.  Assuming 'web' is the name of the service in the docker-compose.yml file
which you wish to exec against, we can create three custom commands in the following example:

- `myapp ls-root` which lists the contents of the root directory within the `web` service container
  and prints it out.
- `myapp ls-root-to-file` which lists the contents of the root directory within the `web` service
  container and dumps to file within the container.
- `myapp tee-file` which takes some text and `tee`s it into another file the `web` service
  container.

```python

def get_ls_root_command(orchestrator: DockerComposeOrchestrator):
    @click.command(
        help="List files in the root directory",
    )
    @click.pass_context
    def ls_root(ctx: click.Context):

        # Equivalent command within the container:
        # `ls -alh`
        cli_context: CliContext = ctx.obj
        output: CompletedProcess = orchestrator.exec(cli_context, "web", ["ls", "-alh", "/"])
        print(output.stdout.decode())

    return ls_root

def get_tee_file_command(orchestrator: DockerComposeOrchestrator):
    @click.command(
        help="Tee some text into a file",
    )
    @click.pass_context
    def tee_file(ctx: click.Context):

        # Equivalent command within the container:
        # `echo "Some data to tee into the custom file" | tee /ls-root.txt`
        cli_context: CliContext = ctx.obj
        output: CompletedProcess = orchestrator.exec(cli_context, "web", ["tee", "/my_custom_file.txt"], stdin_input="Some data to tee into the custom file")

    return tee_file

def get_ls_root_to_file_command(orchestrator: DockerComposeOrchestrator):
    @click.command(
        help="List files in the root directory and tee to file",
    )
    @click.pass_context
    def ls_root_to_file(ctx: click.Context):

        # Equivalent command within the container:
        # `ls -alh | tee /ls-root.txt`
        cli_context: CliContext = ctx.obj
        output: CompletedProcess = orchestrator.exec(cli_context, "web", ["ls", "-alh", "/"])
        data = output.stdout.decode()
        orchestrator.exec(cli_context, "web", ["tee", "/ls-root.txt"], stdin_input=data)

    return ls_root_to_file

def main():
    orchestrator = DockerComposeOrchestrator(Path("docker-compose.yml"))
    configuration = Configuration(
        app_name="appcli_nginx",
        docker_image="thomas-anderson-bsl/appcli-nginx",
        seed_app_configuration_file=Path(BASE_DIR, "resources/settings.yml"),
        stack_configuration_file=Path(BASE_DIR, "resources/stack-settings.yml"),
        baseline_templates_dir=Path(BASE_DIR, "resources/templates/baseline"),
        configurable_templates_dir=Path(BASE_DIR, "resources/templates/configurable"),
        orchestrator=orchestrator,
        custom_commands={get_tee_file_command(orchestrator),get_ls_root_command(orchestrator),get_ls_root_to_file_command(orchestrator)}
    )
    cli = create_cli(configuration)
    cli()

```

### Build configuration template directories

- Store any Jinja2 variable definitions you wish to use in your configuration
  template files in `resources/settings.yml`.
- Store any application context files in `resources/templates/appcli/context/`
- Store any appcli stack specific keys in `resources/stack-settings.yml`.
- Store your `docker-compose.yml`/`docker-compose.yml.j2` file in `resources/templates/baseline/`.
- Configuration files (Jinja2 compatible templates or otherwise) can be stored in one
  of two locations:
  - `resources/templates/baseline` - for templates which the end user **is not** expected to modify.
  - `resources/templates/configurable` - for templates which the end user is expected to modify.

#### Application context files

Template files are templated with Jinja2. The 'data' passed into the templating engine
is a combination of the `settings.yml` and all application context files
(stored in `resources/templates/appcli/context`, and referenced in the `Configuration`
object as `application_context_files_dir`). Application context files that have the
extension `.j2` are templated using the settings from `settings.yml`.

These are combined to make the data for templating as follows:

```json
{
  "settings": {
    ... all settings from `settings.yml`
  },
  "application": {
    <app_context_file_1>: {
      ... settings from `app_context_file_1.yml`, optionally jinja2 templated using settings from `settings.yml`
    },
    ... additional app_context_files
  }
}
```

As a minimal example with the following YAML files:

```yaml
# ./settings.yml
main_settings:
  abc: 123

# ./resources/templates/appcli/context/app_constants.yml
other_settings:
  hello: world

# ./resources/templates/appcli/context/app_variables.yml.j2
variables:
  main_abc_setting: {{ settings.main_settings.abc }}
```

The data for Jinja2 templating engine will be:

```json
{
  "settings": {
    "main_settings": {
      "abc": 123
    }
  },
  "application": {
    "app_constants": {
      "other_settings": {
        "hello": "world"
      }
    },
    "app_variables": {
      "variables": {
        "main_abc_setting": 123
      }
    }
  }
}
```

### Configure application backup

Appcli's `backup` command creates backups of configuration and data of an application, stored
locally in the backup directory. The settings for backups are configured through entries in a
`backups` block in `stack-settings.yml`.

The available keys for entries in the `backups` block are:

| key            | Description                                                                                                       |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| name           | The name of the backup. Must be unique between backup definitions and use `kebab-case`.                           |
| backup_limit   | The number of local backups to keep. Set to `0` to disable rolling deletion.                                      |
| file_filter    | The file_filter contains lists of glob patterns used to specify what files to include or exclude from the backup. |
| frequency      | The cron-like frequency at which backups will execute.                                                            |
| remote_backups | The list of remote backup strategies.                                                                             |

    # filename: stack-settings.yml

    backups:
      - name: "full"
        backup_limit: 0
        file_filter:
          data_dir:
            include_list:
            exclude_list:
          conf_dir:
            include_list:
            exclude_list:
        frequency: "* * *"
        remote_backups:

#### Backup name

The backup `name` is a short descriptive name for the backup definition.
To avoid problems, we _highly_ recommend `name` be:

- unique between items in the `backups` list
- use `kebab-case`

Examples of good names:

- `full`
- `conf-only`
- `audit-logs`

Without a unique `name`, backups from different items in `backups` will
overwrite each other without warning.

Using `kebab-case` is necessary to avoid some issues with `click` and filesystem
naming issues.

When using the `backup` command, you are able to supply the name
of the backup to run. If you have a backup `name` with a space in it, the `click`
library cannot interpret the name as a whole string (even with quotes), so you
will be unable to run the backup individually.

If the backup `name` doesn't use `kebab-case`, it may use some characters that
are incompatible with file and directory naming conventions. Appcli will
automatically slugify the name to something compatible, but this may cause
collisions in the folder names of backups to be taken which will lead to backups
being overwritten. e.g. `s3#1` and `s3&1` will both translate internally to
`s3-1`.

#### Backup limit

A rolling deletion strategy is used to remove local backups, in order to keep `backup_limit` number
of backups.

If more than `backup_limit` number of backups exist in the backup directory, the oldest backups will
be deleted.

Set this value to `0` to keep all backups.

#### File filter

The `file_filter` block enables filtering of files to backup from `conf` and `data` directories. For
more details including examples, see [here](/README_BACKUP_FILE_FILTER.md).

    # filename: stack-settings.yml
    # Includes all log files from data dir only

    backups:
      - name: "full"
        backup_limit: 0
        file_filter:
          data_dir:
            include_list:
              - "**/*.log"
            exclude_list:
            conf_dir:
              include_list:
              exclude_list:
                - "**/*"
        frequency: "* * *"
        remote_backups:

#### Freqency

Appcli supports limiting individual backups to run on only specific days using a cron-like frequency
filter.

When the `backup` command is run, each backup strategy will check if the `frequency` pattern matches
today's date. Only strategies whose `frequency` pattern match today's date will execute.

The input pattern `pattern` is prefixed with `"* * "` and is used as a standard cron expression to
check for a match. i.e. `"* * $pattern"`.

Examples:

- `"* * *"` (cron equivalent `"* * * * *"`) will always run.
- `"* * 0"` (cron equivalent `"* * * * 0"`) will only run on Sunday.
- `"1 */3 *"` (cron equivalent `"* * 1 */3 *"`) will only run on the first day-of-month of every 3rd
  month.

#### Remote backup

Appcli supports pushing local backups to remote storage. The list of strategies for pushing to
remote storage are defined within the `remote_backups` block.

The available keys for every remote backup strategy are:

| key           | Description                                                                                                 |
| ------------- | ----------------------------------------------------------------------------------------------------------- |
| name          | A short name or description used to describe this backup.                                                   |
| strategy_type | The type of this backup, must match an implemented remote backup strategy.                                  |
| frequency     | The cron-like frequency at which remote backups will execute. Behaves the same as local backup `frequency`. |
| configuration | Custom configuration block that is specific to each remote backup strategy.                                 |

N.B. remote backups will only run for a local backup that has run. Therefore the `frequency` of the
local backup will apply first, followed by the `frequency` of the remote backup. This means that
it's possible to write a remote backup frequency that will never execute. e.g. Local `* * 0` and
remote `* * 1`.

##### Strategies

###### AWS S3 remote strategy

To use S3 remote backup, set `strategy_type` to `S3`.
The available configuration keys for an S3 backup are:

| key         | Description                                                                                                                 |
| ----------- | --------------------------------------------------------------------------------------------------------------------------- |
| bucket_name | The name of the bucket to upload to.                                                                                        |
| access_key  | The AWS Access key ID for the account to upload with.                                                                       |
| secret_key  | The AWS Secret access key for the account to upload with. The value _must_ be encrypted using the appcli `encrypt` command. |
| bucket_path | The path in the S3 bucket to upload to. Set this to an empty string to upload to the root of the bucket.                    |
| tags        | Key value pairs of tags to set on the backup object.                                                                        |

    # filename: stack-settings.yml

    backups:
      - name: "full_backup"
        backup_limit: 0
        remote_backups:
        - name: "weekly_S3"
          strategy_type: "S3"
          frequency: "* * 0"
          configuration:
            bucket_name: "aws.s3.bucket"
            access_key: "aws_access_key"
            secret_key: "enc:id=1:encrypted_text:end"
            bucket_path: "bucket/path"
            tags:
              frequency: "weekly"
              type: "data"

### Restoring a remote backup

To restore from a remote backup:

1. Acquire the remote backup (`.tgz` file) that you wish to restore. For S3 this can be done by
   downloading the backup from the specified bucket.
2. Place the backup `myapp_date.tgz` file in the backup directory. By default this will be
   `/opt/brightsparklabs/${APP_NAME}/production/backup/`
3. Confirm that appcli can access the backup by running the `view-backups` command
4. Run the restore command `./myapp restore BACKUP_FILE.tgz` e.g.
   `./myapp restore APP_2021-02-02T10:55:48+00:00.tgz`. The restore process will trigger a backup.

### Define a container for your CLI application

    # filename: Dockerfile

    FROM brightsparklabs/appcli

    ENTRYPOINT ["./myapp.py"]
    WORKDIR /app

    # install compose if using it as the orchestrator
    RUN pip install docker-compose

    COPY requirements.txt .
    RUN pip install --requirement requirements.txt
    COPY src .

    ARG APP_VERSION=latest
    ENV APP_VERSION=${APP_VERSION}

### Build the container

    # sh
    docker build -t brightsparklabs/myapp --build-arg APP_VERSION=latest .

### (Optional) Login to private Docker registries and pass through credentials

It is possible to login to private Docker registries on the host, and pass through credentials to
the CLI container run by the launcher script. This enables pulling and running Docker images from
private Docker registries.

Login using:

    docker login ${REGISTRY_URL}

The credentials file path can be passed as an option via `--docker-credentials-file` or `-p` to the
`myapp` container.

### View the installer script

    # sh
    docker run --rm brightsparklabs/myapp:<version> install

    # or if using a private registry for images
    docker run --rm brightsparklabs/myapp:<version> \
      --docker-credentials-file ~/.docker/config.json \
      install

While it is not mandatory to view the script before running, it is highly recommended.

### Run the installer script

    # sh
    docker run --rm brightsparklabs/myapp:<version> install | sudo bash

The above will use the following defaults:

- `environment` => `production`.
- `install-dir` => `/opt/brightsparklabs/${APP_NAME}/production/`.
- `configuration-dir` => `/opt/brightsparklabs/${APP_NAME}/production/conf/`.
- `data-dir` => `/opt/brightsparklabs/${APP_NAME}/production/data/`.
- `backup-dir` => `/opt/brightsparklabs/${APP_NAME}/production/backup/`.

You can modify any of the above if desired. E.g.

    # sh
    docker run --rm brightsparklabs/myapp:<version> \
        --environment "uat" \
        --configuration-dir /etc/myapp \
        --data-dir /mnt/data/myapp \
        install --install-dir ${HOME}/apps/myapp \
    | sudo bash

Where:

- `--environment` defines the environment name for the deployment. This allows multiple instances of
  the application to be present on the same host.
  Defaults to `production`.
- `--install-dir` defines the base path for launcher and the default locations for the configuration
  and data directories if they are not overrideen (see below).
  Defaults to `/opt/brightsparklabs/${APP_NAME}/${ENVIRONMENT}/` (where `${ENVIRONMENT}` is defined
  by `--environment` above).
- `--configuration-dir` defines the path to the configuration directory.
  Defaults to `${INSTALL_DIR}/conf/` (`${INSTALL_DIR}` is defined by `--install-dir` above).
- `--data-dir` defines the path to the data directory.
  Defaults to `${INSTALL_DIR}/data/` (`${INSTALL_DIR}` is defined by `--install-dir` above).

The installation script will generate a launcher script for controlling the application. The script
location will be printed out when running the install script. This script should now be used as the
main entrypoint to all appcli functions for managing your application.

## Migration from appcli version <=1.3.6 to version >1.3.6

As a result of supporting application context files, all references to
settings in template files have moved.

All settings in `settings.yml` used in templating are now namespaced under
`settings`. All templates will need to change their references to use this new
namespacing scheme. For example, in templates that refer to settings, change the
references like so:

- `my_app.server.hostname` -> `settings.my_app.server.hostname`
- `my_app.server.http.port` -> `settings.my_app.server.http.port`

## Usage

This section details what commands and options are available.

### Top-level Commands

To be used in conjunction with your application `./myapp <command>` e.g. `./myapp configure init`

| Command      | Description                                                       |
| ------------ | ----------------------------------------------------------------- |
| backup       | Create a backup of application data and configuration.            |
| configure    | Configures the application.                                       |
| encrypt      | Encrypts the specified string.                                    |
| init         | Initialises the application.                                      |
| launcher     | Outputs an appropriate launcher bash script.                      |
| migrate      | Migrates the configuration of the application to a newer version. |
| orchestrator | Perform docker orchestration                                      |
| restore      | Restore a backup of application data and configuration.           |
| service      | Lifecycle management commands for application services.           |
| task         | Commands for application tasks.                                   |
| version      | Fetches the version of the app being managed with appcli.         |
| view-backups | View a list of locally-available backups.                         |

### Options

| Option                             | Description                                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| --debug                            | Enables debug level logging.                                                                                        |
| -c, --configuration-dir PATH       | Directory containing configuration files. [This is required unless subcommand is one of: `install`.                 |
| -d, --data-dir PATH                | Directory containing data produced/consumed by the system. This is required unless subcommand is one of: `install`. |
| -t, --environment TEXT             | Deployment environment the system is running in. Defaults to `production`.                                          |
| -p, --docker-credentials-file PATH | Path to the Docker credentials file (config.json) on the host for connecting to private Docker registries.          |
| -a, --additional-data-dir TEXT     | Additional data directory to expose to launcher container. Can be specified multiple times.                         |
| -e, --additional-env-var TEXT      | Additional environment variables to expose to launcher container. Can be specified multiple times.                  |
| --help                             | Show the help message and exit.                                                                                     |

#### Command: `backup`

Creates a backup `.tgz` file in the backup directory that contains files from the configuration and
data directory, as configured in `stack-settings.yml`. After the backup is taken, remote backup
strategies will be executed (if applicable).

usage: `./myapp backup [OPTIONS] [ARGS]`

| Option                                         | Description                                        |
| ---------------------------------------------- | -------------------------------------------------- |
| --pre-stop-services/--no-pre-stop-services     | Whether to stop services before performing backup. |
| --post-start-services/--no-post-start-services | Whether to start services after performing backup. |
| --help                                         | Show the help message and exit.                    |

The `backup` command optionally takes an argument corresponding to the `name` of the backup to run.
If no `name` is provided, all backups will attempt to run.

#### Command Group: `configure`

Configures the application.

usage: `./myapp configure [OPTIONS] COMMAND [ARGS]`

| Command    | Description                                                                                                               |
| ---------- | ------------------------------------------------------------------------------------------------------------------------- |
| apply      | Applies the settings from the configuration.                                                                              |
| diff       | Get the differences between current and default configuration settings.                                                   |
| get        | Reads a setting from the configuration.                                                                                   |
| get-secure | Reads a setting from the configuration, decrypting if it is encrypted. This will prompt for the setting key.              |
| init       | Initialises the configuration directory.                                                                                  |
| set        | Saves a setting to the configuration. Allows setting the type of value with option `--type`, and defaults to string type. |
| template   | Configures the baseline templates.                                                                                        |
| edit       | Open the settings file for editing with vim-tiny.                                                                         |

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `encrypt`

Encrypts the specified string.

usage: `./myapp encrypt [OPTIONS] TEXT`

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command Group: `init`

Initialises the application.

usage: `./myapp init [OPTIONS] COMMAND [ARGS]`

| Command  | Description                                                              |
| -------- | ------------------------------------------------------------------------ |
| keycloak | Initialises a Keycloak instance with BSL-specific initial configuration. |

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `launcher`

Outputs an appropriate launcher bash script to stdout.

usage: `./myapp launcher [OPTIONS]`

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `migrate`

Migrates the application configuration to work with the current application version.

usage: `./myapp migrate [OPTIONS]`

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command Group: `orchestrator`

Perform tasks defined by the orchestrator.

usage: `./myapp orchestrator [OPTIONS] COMMAND [ARGS]`

All commands are defined within the orchestrators themselves. Run `./myapp orchestrator` to list
available commands.

For example, the following commands are available to docker-compose:

| Command | Description                                                                                                        |
| ------- | ------------------------------------------------------------------------------------------------------------------ |
| ps      | List containers for the appcli project, with current status and exposed ports.                                     |
| compose | Run a docker compose command. See [docker compose](https://docs.docker.com/engine/reference/commandline/compose/). |

| Option | Description                    |
| ------ | ------------------------------ |
| --help | Show the help message and exit |

#### Command: `restore`

Restores a specified backup `.tgz` file from the configured backup folder.

usage: `./myapp restore BACKUP_FILE`

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command Group: `service`

Runs application services. These are the long-running services which should only exit on command.

usage: `./myapp service [OPTIONS] COMMAND [ARGS]`

| Command  | Description                                                                                                                                                                                                             |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| logs     | Prints logs from all services.                                                                                                                                                                                          |
| shutdown | Shuts down the system. If one or more service names are provided, shuts down the specified service(s) only.                                                                                                             |
| start    | Starts the system. If one or more service names are provided, starts the specified service(s) only.                                                                                                                     |
| restart  | Restarts service(s) (`shutdown` followed by `start`). Optionally run a `configure apply` during the restart with the `--apply` flag. If one or more service names are provided, restarts the specified service(s) only. |
| status   | Lists all containers for the appcli project, with current status and exposed ports. If one or more service names are provided, lists the status and 
 exposed ports of the specified service(s) only. |

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command Group: `task`

Runs application tasks. These are short-lived services which should exit when the task is complete.

usage: `./myapp task [OPTIONS] COMMAND [ARGS]`

| Command | Description                                                                                  |
| ------- | -------------------------------------------------------------------------------------------- |
| run     | Runs a specified application task. Optionally run in the background with `-d/--detach` flag. |

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `version`

Fetches the version of the app being managed with appcli.

usage: `./myapp version`

#### Command: `view-backups`

View a list of all backups in the configured backup folder.

usage: `./myapp view-backups`

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

### Usage within scripts and cron

By default, the generated `appcli` launcher script will run the CLI container with a virtual
terminal session (tty).  This may interfere with crontab entries or scripts that use the appcli
launcher.

To disable tty when running the launcher script, set `NO_TTY` environment variable to `true`.

    NO_TTY=true ./myapp [...]

or

    export NO_TTY=true
    ./myapp [...]

If required, you can also disable interactive mode with the `NO_INTERACTIVE` environment variable.

    NO_INTERACTIVE=true ./myapp [...]

or

    export NO_INTERACTIVE=true
    ./myapp [...]

## Development

This section details how to build/test/run/debug the system in a development environment.

### Prerequisites

The following must be installed and in the `PATH`:

- make
- python 3.7+
- virtualenv
- git

### Build

    make all

### Install

    pip install -e .

### Running unit tests

    make test

## Usage while developing your CLI application

While developing, it may be preferable to run your python script directly rather than having to
rebuild a container each time you update it.

- Ensure docker is installed (more specifically a docker socket at `/var/run/docker.sock`).
- Set the environment variables which the CLI usually sets for you:

        export \
            MYAPP_DATA_DIR=/tmp/myapp/data \
            MYAPP_CONFIG_DIR=/tmp/myapp/config \
            MYAPP_GENERATED_CONFIG_DIR=/tmp/myapp/config/.generated \
            MYAPP_BACKUP_DIR=/tmp/myapp/backup \
            MYAPP_ENVIRONMENT=dev
- Run your CLI application:

        ./src/myapp.py \
              --debug \
              --configuration-dir "${MYAPP_CONFIG_DIR}" \
              --data-dir "${MYAPP_DATA_DIR}" \
              --backup-dir "${MYAPP_BACKUP_DIR}" \
              --environment "${MYAPP_ENVIRONMENT}

## Contributing

When committing code, call `make all` to automatically run code formatting/ linting/testing.

Appcli uses the python code formatter [black](https://pypi.org/project/black/) with default
settings. This ensures that PR diffs are minimal and focussed on the code change rather than
stylistic coding decisions.

Install with `pip install black`. This can be run through VSCode or via the CLI. See the `black`
documentation for details.

## Licenses

Refer to the `LICENSE` file for details.

This project makes use of several libraries and frameworks. Refer to the `LICENSES` folder for
details.
