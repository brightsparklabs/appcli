# BSL Application CLI Library

A library for adding CLI interfaces to applications in the brightSPARK Labs
style.

## Overview

This library can be leveraged to add a standardised CLI capability to
applications to handle system lifecycle events (start, stop, configure,
migrate, etc).

The CLI is designed to run within a Docker container and launch other Docker
containers (i.e. Docker-in-Docker). This is generally managed via a
`docker-compose.yml` file.

The library exposes the following environment variables to the `docker-compose.yml` file:

- `APP_VERSION` - the version of containers to launch
- `<APP_NAME>_CONFIG_DIR` - the directory containing configuration files
- `<APP_NAME>_DATA_DIR` - the directory containing data produced by the system.
- `<APP_NAME>_GENERATED_CONFIG_DIR` - the directory containing configuration
  files generated from the templates in `<APP_NAME>_CONFIG_DIR`.
- `<APP_NAME>_ENVIRONMENT` - the 'environment' of the application to be run. For
  example `production` or `staging`. This allows multiple instances of the same
  project to run on the same docker daemon. Defaults to 'production'.

The `docker-compose.yml` can be templated by renaming to `docker-compose.yml.j2`, and
setting variables within the `settings.yml` file as described in the Usage section.

## Usage

- Add the library to your python CLI application:

        pip install git+https://github.com/brightsparklabs/appcli.git@<VERSION>

- Define the CLI for your application `myapp`:

        # filename: myapp

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
                  Path('docker-compose.yml')
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

- Store any Jinja2 variable definitions you wish to use in your configuration
  template files in `resources/settings.yml`.
- Store your `docker-compose.yml`/`docker-compose.yml.j2` file in `resources/templates/baseline/`.
- Configuration files (Jinja2 compatible templates or otherwise) can be stored in one
  of two locations:
  - `resources/templates/baseline` - for templates which the end user **is not** expected to modify.
  - `resources/templates/configurable` - for templates which the end user is expected to modify.
- Define a container for your CLI application:

        # filename: Dockerfile

        FROM brightsparklabs/appcli

        ENTRYPOINT ["./myapp"]
        WORKDIR /app

        # install compose if using it as the orchestrator
        RUN pip install docker-compose

        COPY requirements.txt .
        RUN pip install --requirement requirements.txt
        COPY src .

        ARG APP_VERSION=latest
        ENV APP_VERSION=${APP_VERSION}

- Build the container:

        # sh
        docker build -t brightsparklabs/myapp --build-arg APP_VERSION=latest .

- Generate a launcher script `myapp.sh`:

        # sh
        docker run brightsparklabs/myapp \
            --configuration-dir /path/to/myapp/conf \
            --data-dir /path/to/myapp/data \
            --environment "production" \
            --additional-data-dir "EXTRA_DATA"="/path/to/extra/data" \
            --additional-env-var "ENV_VAR_2"="Some value here" \
            launcher \
        > myapp.sh

        chmod +x myapp.sh

This script, `myapp.sh` should now be used as the main entrypoint to all appcli
functions for managing your application.

## Development

This section details how to build/test/run/debug the system in a development
environment.

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

While developing, it may be preferable to run your python script directly
rather than having to rebuild a container each time you update it.

- Ensure docker is installed (more specifically a docker socket at
  `/var/run/docker.sock`).
- Set the environment variables which the CLI usually sets for you:

        export MYAPP_CONFIG_DIR=/tmp/myapp/config \
               MYAPP_DATA_DIR=/tmp/myapp/data

- Run your CLI application:

        ./myapp \
          --debug \
          --configuration-dir "${MYAPP_CONFIG_DIR}" \
          --data-dir "${MYAPP_DATA_DIR}"

## Contributing

When committing code, call `make all` to automatically run code formatting/
linting/testing.

Appcli uses the python code formatter [black](https://pypi.org/project/black/)
with default settings. This ensures that PR diffs are minimal and focussed on
the code change rather than stylistic coding decisions.

Install with `pip install black`. This can be run through VSCode or via the
CLI. See the `black` documentation for details.

## Licenses

Refer to the `LICENSE` file for details.

This project makes use of several libraries and frameworks. Refer to the
`LICENSES` folder for details.
