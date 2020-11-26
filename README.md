# BSL Application CLI Library

[![Build Status](https://travis-ci.org/brightsparklabs/appcli.svg?branch=develop)](https://travis-ci.org/brightsparklabs/appcli)

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
- `<APP_NAME>_ENVIRONMENT` - the deployment environment the system is running in. For example
  `production` or `staging`. This allows multiple instances of the application to run on the same
  Docker daemon. Defaults to `production`.

The `docker-compose.yml` can be templated by renaming to `docker-compose.yml.j2`, and setting
variables within the `settings.yml` file as described in the Installation section.

## Installation

### Add the library to your python CLI application

    pip install git+https://github.com/brightsparklabs/appcli.git@<VERSION>

### Define the CLI for your application `myapp`

    # filename: myapp.py

    #!/usr/bin/env python3
    # # -*- coding: utf-8 -*-

    # standard libraries
    import os
    import sys
    from pathlib import Path

    # vendor libraries
    import appcli

    # ------------------------------------------------------------------------------
    # CONSTANTS
    # ------------------------------------------------------------------------------

    # directory containing this script
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def main():
        configuration = appcli.Configuration(
            app_name='myapp',
            docker_image='brightsparklabs/myapp',
            seed_app_configuration_file=Path(BASE_DIR, 'resources/settings.yml'),
            baseline_templates_dir=Path(BASE_DIR, 'resources/templates/baseline'),
            configurable_templates_dir=Path(BASE_DIR, 'resource/templates/configurable'),
            orchestrator=appcli.DockerComposeOrchestrator(
                docker_compose_file = Path("docker-compose.yml"),
                docker_compose_override_directory = Path("docker-compose.override.d/"),
                docker_compose_task_file = Path("docker-compose.tasks.yml"),
                docker_compose_task_override_directory = Path(
                    "docker-compose.tasks.override.d/"
                ),
            ),
            mandatory_additional_data_dirs=["EXTRA_DATA",],
            mandatory_additional_env_variables=["ENV_VAR_2",],
        )
        cli = appcli.create_cli(configuration)
        cli()

    # ------------------------------------------------------------------------------
    # ENTRYPOINT
    # ------------------------------------------------------------------------------

    if __name__ == "__main__":
        main()

### Build configuration template directories

- Store any Jinja2 variable definitions you wish to use in your configuration
  template files in `resources/settings.yml`.
- Store your `docker-compose.yml`/`docker-compose.yml.j2` file in `resources/templates/baseline/`.
- Configuration files (Jinja2 compatible templates or otherwise) can be stored in one
  of two locations:
  - `resources/templates/baseline` - for templates which the end user **is not** expected to modify.
  - `resources/templates/configurable` - for templates which the end user is expected to modify.

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
    docker run --rm brightsparklabs/myapp:<version> --docker-credentials-file ~/.docker/config.json install

While it is not mandatory to view the script before running, it is highly recommended.

### Run the installer script

    # sh
    docker run --rm brightsparklabs/myapp:<version> install | sudo bash

The above will use the following defaults:

- `environment` => `production`.
- `install-dir` => `/opt/brightsparklabs/${APP_NAME}/production/`.
- `configuration-dir` => `/opt/brightsparklabs/${APP_NAME}/production/conf/`.
- `data-dir` => `/opt/brightsparklabs/${APP_NAME}/production/data/`.

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

## Usage

This section details what commands and options are available.

### Top-level Commands

To be used in conjunction with your application `./myapp <command>` e.g. `./myapp configure init`

| Command      | Description                                                       |
| ------------ | ----------------------------------------------------------------- |
| configure    | Configures the application.                                       |
| encrypt      | Encrypts the specified string.                                    |
| init         | Initialises the application.                                      |
| launcher     | Outputs an appropriate launcher bash script.                      |
| migrate      | Migrates the configuration of the application to a newer version. |
| orchestrator | Perform docker orchestration                                      |
| service      | Lifecycle management commands for application services.           |
| task         | Commands for application tasks.                                   |

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

#### Command: `configure`

Configures the application.
usage `./myapp configure [OPTIONS] COMMAND [ARGS]`

| Command  | Description                                                                                                               |
| -------- | ------------------------------------------------------------------------------------------------------------------------- |
| apply    | Applies the settings from the configuration.                                                                              |
| diff     | Get the differences between current and default configuration settings.                                                   |
| get      | Reads a setting from the configuration.                                                                                   |
| init     | Initialises the configuration directory.                                                                                  |
| set      | Saves a setting to the configuration. Allows setting the type of value with option `--type`, and defaults to string type. |
| template | Configures the baseline templates.                                                                                        |
| edit     | Open the settings file for editing with vim-tiny.                                                                         |

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `encrypt`

Encrypts the specified string.
usage `./myapp encrypt [OPTIONS] TEXT`

| Command | Description |
| ------- | ----------- |


No commands available

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `init`

Initialises the application.
usage `./myapp init [OPTIONS] COMMAND [ARGS]`

| Command  | Description                                                              |
| -------- | ------------------------------------------------------------------------ |
| keycloak | Initialises a Keycloak instance with BSL-specific initial configuration. |

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `launcher`

Outputs an appropriate launcher bash script to stdout.
usage `./myapp launcher [OPTIONS]`

| Command | Description |
| ------- | ----------- |


No commands available

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `migrate`

Migrates the application configuration to work with the current application version.
usage `./myapp migrate [OPTIONS]`

| Command | Description |
| ------- | ----------- |


No commands available

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `orchestrator`

Perform tasks defined by the orchestrator.
usage `./myapp orchestrator [OPTIONS] COMMAND [ARGS]`

All commands are defined within the orchestrators themselves. Run `./myapp orchestrator` to list available commands.

| Option | Description                    |
| ------ | ------------------------------ |
| --help | Show the help message and exit |

#### Command: `service`

Runs application services. These are the long-running services which should only exit on command.
usage `./myapp service [OPTIONS] COMMAND [ARGS]`

| Command  | Description                                                                               |
| -------- | ----------------------------------------------------------------------------------------- |
| logs     | Prints logs from all services.                                                            |
| shutdown | Shuts down the system. If a service name is provided, shuts down the single service only. |
| start    | Starts the system. If a service name is provided, starts the single service only.         |

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

#### Command: `task`

Runs application tasks. These are short-lived services which should exit when the task is complete.
usage `./myapp task [OPTIONS] COMMAND [ARGS]`

| Command | Description                        |
| ------- | ---------------------------------- |
| run     | Runs a specified application task. |

| Option | Description                     |
| ------ | ------------------------------- |
| --help | Show the help message and exit. |

### Usage within scripts and cron

By default, the generated `appcli` launcher script will run the CLI container with a virtual terminal session (tty).
This may interfere with crontab entries or scripts that use the appcli launcher.

To disable tty when running the launcher script, set `NO_TTY` environment variable to `true`.

    NO_TTY=true ./myapp [...]

or

    export NO_TTY=true
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

        export MYAPP_CONFIG_DIR=/tmp/myapp/config \
               MYAPP_DATA_DIR=/tmp/myapp/data

- Run your CLI application:

        ./myapp \
          --debug \
          --configuration-dir "${MYAPP_CONFIG_DIR}" \
          --data-dir "${MYAPP_DATA_DIR}"

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
