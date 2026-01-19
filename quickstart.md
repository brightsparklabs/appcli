# Quick Start

This guide will help you get started with standing up a sample `appcli` application.

### Prerequisites

- python
- docker
- docker-compose

### Setup the appcli enironment

#### Create the required directory structure

Run the following commands to create the required files and folders

```bash
mkdir -p src/resources/templates/{baseline,configurable}
touch src/resources/settings.yml
touch src/resources/stack-settings.yml
```

#### Create the appcli application

```bash
touch src/myapp.py
chmod +x src/myapp.py

cat <<EOF >src/myapp.py
#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# Standard libraries.
import sys
from pathlib import Path

# Vendor libraries.
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
            docker_compose_file = Path('docker-compose.yml')
        ),
    )
    cli = create_cli(configuration)
    cli()

# ------------------------------------------------------------------------------
# ENTRYPOINT
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    main()

EOF
```

### Create Dockerfile

```bash
cat <<EOF >Dockerfile
FROM brightsparklabs/appcli-docker-compose:<version>

ENTRYPOINT ["./myapp.py"]
WORKDIR /app

COPY requirements.txt .
RUN pip install --requirement requirements.txt
COPY src .

ARG APP_VERSION=latest
ENV APP_VERSION=\${APP_VERSION}

EOF
```

We can see in the `Dockerfile`, it is referring to a `requirements.txt` file which we will need to
create:

```bash
APPCLI_VERSION=<version>

echo "bsl-appcli==${APPCLI_VERSION}" >> requirements.txt
```

### Create docker-compose.yml

```bash
cat <<EOF >src/resources/templates/baseline/docker-compose.yml

version: '3'
services:
  echo-server:
    image: ealen/echo-server:0.5.1

EOF
```

The above uses [Echo-Server](https://ealenn.github.io/Echo-Server/pages/quick-start/docker.html#run)
as our example application.

### Directory check

Before we build our application please make sure your directory reflects the following structure:

```
├── src
│   ├── resources
│   │   ├── settings.yml
│   │   ├── stack-settings.yml
│   │   └── templates
│   │           ├── baseline
│   │           │       └── docker-compose.yml
│   │           └── configurable
│   └── myapp.py
├── requirements.txt
└── Dockerfile
```

### Build the container

```
docker build -t brightsparklabs/myapp:latest --build-arg APP_VERSION=latest .
```

### Run the installed script.

While it is not mandatory to view the script before running, it is highly recommended.

```bash
docker run --rm brightsparklabs/myapp:latest install
```

Once you can successfully see the script printed on the command line, you are ready to install

```bash
docker run --rm brightsparklabs/myapp:latest install | sudo bash
```

### Initialising and Applying settings.

By default, appcli will auto `init` and auto `apply` itself. It is possible to manually perform
these steps by disabling `auto_configure` in __either__ the `my-app.py` script, or when generating
the install script:

#### Option 1: In Python Script

```python
# Disable auto_configure in the `myapp.py` script.
configuration = Configuration(
    app_name="myapp",
    auto_configure_on_install=False,
)
```

#### Option 2: In Bash Script

```bash
# Disable auto_configure in the `install` script.
docker run --rm brightsparklabs/myapp:latest install | sudo bash --auto-configure=false
# Manually apply the connfigurations.
/opt/brightsparklabs/myapp/production/myapp configure init
/opt/brightsparklabs/myapp/production/myapp configure apply
```

### Running the service

If you type in `service`, it will list all the commands you can use to control the services. The main
ones are `service start` and `service stop`:

```bash
/opt/brightsparklabs/myapp/production/myapp service start
```

You can check to see if your service is still running by typing in the following:

```bash
docker ps
```

More commands can be found in the [appcli README](https://github.com/brightsparklabs/appcli).

## Local Development

Instead of fetching appcli from the PIP repository, you can import appcli from the local filesystem into your project (this can help during development).

First, clone the appcli repository into the same directory as the `requirements.txt` file:

```bash
git clone git@github.com:brightsparklabs/appcli.git
```

Change the `requirements.txt` file to reference the local appcli repository:

```
-e . /appcli
```

Finally, copy the appcli repo to the docker image (in the `Dockerfile`):

```
COPY appcli .
```
