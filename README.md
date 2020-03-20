# BSL Application CLI Library

A library for adding CLI interfaces to applications in the brightSPARK Labs
style.

## Overview

This library can be leveraged to add a standardised CLI capability to
applications to handle system lifecycle events (start, stop, configure, etc).

The CLI is designed to run within a Docker container and launch other Docker
containers (i.e. Docker-in-Docker). This is generally managed via a
`docker-compose.yml` file.

The library leverages the following environment variables:

- `APP_VERSION` - the version of containers to launch.
- `<APP_NAME>_CONFIG_DIR` - the directory containing configuration files
  consumed by the system.
- `<APP_NAME>_DATA_DIR` - the directory containing data produced by the system.
- `APPCLI_MANAGED` - a flag indicating that the environment currently running
  was created by the `appcli` library.
- `<APP_NAME>_GENERATED_CONFIG_DIR` - the directory containing configuration
  files generated from the templates in `<APP_NAME>_CONFIG_DIR`. This is only
  set in environments which have the `APPCLI_MANAGED` flag.
- `<APP_NAME>_ENVIRONMENT` - the 'environment' of the application to be run. For
  example `production` or `staging`. This allows multiple instances of the same
  project to run on the same docker daemon. If undefined, this defaults to 'default'.

## Usage

- Add the library to your python CLI application:

        pip install git+https://github.com/brightsparklabs/appcli.git@<VERSION>

- Define the CLI for your application:

        # filename: myapp

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
                seed_app_configuration_file=Path(BASE_DIR, 'resources/myapp.yml'),
                seed_templates_dir=Path(BASE_DIR, 'resources/templates')
            )
            cli = appcli.create_cli(configuration)
            cli()

        # ------------------------------------------------------------------------------
        # ENTRYPOINT
        # ------------------------------------------------------------------------------

        if __name__ == "__main__":
            main()

- Store any Jinja2 variable definitions you wish to use in your configuration
  template files in `resources/myapp.yml`.
- Store your `docker-compose.yml.j2` file under `resources/templates/cli/`.
- Store any other Jinja2 configuration template files under
  `resources/templates`.
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

- Launch the system via your container:

        # sh
        export MYAPP_CONFIG_DIR=/tmp/myapp/config \
               MYAPP_DATA_DIR=/tmp/myapp/data

        docker run \
            --volume /var/run/docker.sock:/var/run/docker.sock \
            brightsparklabs/myapp \
                --debug \
                --configuration-dir "${MYAPP_CONFIG_DIR}" \
                --data-dir "${MYAPP_DATA_DIR}"

## Usage while developing your CLI application

While developing, it may be preferable to run your python script directly
rather than having to rebuild a container each time you update it.

- Ensure docker is installed (more specifically a docker socket at
  `/var/run/docker.sock`).
- Set the environment variables which the CLI usually sets for you:

        export APP_VERSION=latest \
            APPCLI_MANAGED=Y \
            MYAPP_CONFIG_DIR=/tmp/myapp/config \
            MYAPP_DATA_DIR=/tmp/myapp/data \
            MYAPP_GENERATED_CONFIG_DIR=/tmp/myapp/config/.generated

- Run your CLI application:

        ./myapp \
          --debug \
          --configuration-dir "${MYAPP_CONFIG_DIR}" \
          --data-dir "${MYAPP_DATA_DIR}"

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

## Contributing

When committing code, first run the python code formatter
[black](https://pypi.org/project/black/) with default settings. This will
ensure that PR diffs are minimal and focussed on the code change rather than
stylistic coding decisions.

Install with `pip install black`. This can be run through VSCode or via the
CLI. See the documentation for details.

## Licenses

Refer to the `LICENSE` file for details.

This project makes use of several libraries and frameworks. Refer to the
`LICENSES` folder for details.
