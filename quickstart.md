# QuickStart

This guide will help you get started with standing up a sample appcli application.

### Prerequisites

- python
- docker
- docker-compose

### Setup the appcli enironment

#### Create the required directory structure

Run the following commands to create the required files and folders

```bash
mkdir -p src/resources/templates/{baseline,configurable}
touch src/resources/myapp.py
touch src/resources/settings.py
touch src/resources/stack-settings.py
```
Navigate to the newly created `myapp.py` file. Paste in the folllowing code

```python
#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# filename: myapp.py

# standard libraries
import os
import sys
from pathlib import Path

# vendor libraries
from appcli.cli_builder import create_cli
from appcli.models.configuration import Configuration
from appcli.orchestrators import DockerComposeOrchestrator

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# directory containing this script
BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# ------------------------------------------------------------------------------
# PRIVATE METHODS
# ------------------------------------------------------------------------------

def main():
    configuration = Configuration(
        app_name='myapp',
        docker_image='brightsparklabs/myapp',
        seed_app_configuration_file=Path(BASE_DIR, 'resources/settings.yml'),
        stack_configuration_file=Path(BASE_DIR, 'resources/stack-settings.yml'),
        baseline_templates_dir=Path(BASE_DIR, 'resources/templates/baseline'),
        configurable_templates_dir=Path(BASE_DIR, 'resources/templates/configurable'),
        orchestrator=DockerComposeOrchestrator(
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
```

Make sure the `myapp.py` has executable permission. In order to do this, you need to cd into the directory of myapp.py in your terminal and execute the following command

```bash
chmod +x myapp.py
```

### Dockerfile Setup

Outside of the `src` folder, create a docker file and paste in the following settings so we can assemble our image

```Dockerfile
# filename: Dockerfile

FROM brightsparklabs/appcli

ENTRYPOINT ["./myapp.py"]
WORKDIR /app

# Install compose if using it as the orchestrator.
RUN pip install docker-compose

COPY requirements.txt .
RUN pip install --requirement requirements.txt
COPY src .

ARG APP_VERSION=latest
ENV APP_VERSION=${APP_VERSION}
```

We can see in the `Dockerfile`, it is referring to a `requirements.txt` file which we will need to create. Go ahead and create a `requirements.txt` file in the same location as your Dockerfile and enter in the following `bsl-appcli==1.3.4` 
This will install the appcli package in the image.

### Create a docker compose file
You will need to create a docker compose file which will be placed in the baseline folder. Give it the default name `docker-compose.yml`

We will be using an Echo-Server for our example application which is useful for testing purposes as it replicates the request sent by the client and sends it back. More information on this container can be found [here](https://ealenn.github.io/Echo-Server/pages/quick-start/docker.html#run)

Paste in the following code into your docker compose file.

```yaml
version: '3'
services:
  echo-server:
    image: ealen/echo-server:0.5.1
```


### Directory check

Before we build our application please make sure your directory reflects the following structure:

```
├── src
│   ├── resources
│   │   ├── settings.yml
│   │   ├── stack-settings.yml
│   │   ├── templates
|   |           ├── baseline
|   |           |       ├── docker-compose.yml
|   |           ├── configurable
|   | 
│   ├── myapp.py
|
├── requirements.txt
├── Dockerfile    
```


### Build the container

```
docker build -t brightsparklabs/myapp --build-arg APP_VERSION=latest .
```

### Run the installed script.

While it is not mandatory to view the script before running, it is highly recommended.

```
docker run --rm brightsparklabs/myapp:latest install
```

Once you can successfully see the script printed on the command line, you are ready to install

```
docker run --rm brightsparklabs/myapp:latest install | sudo bash` 
```

### Initialise

Once you have successfully ran the install script you can initialise the app by typing in the following command

```
/opt/brightsparklabs/myapp/production/myapp configure init`
```

### Applying the settings

Before starting the services we need to run the configure apply command which will apply  the settings from the configuration.

```
/opt/brightsparklabs/myapp/production/myapp configure apply
```

### Running the service

If you type in service, it will list all the commands you can use to control the services. The main ones are `service start` and `service stop`

```
/opt/brightsparklabs/myapp/production/myapp service start
```

You can check to see if your service is still running by typing in the following docker command

```
docker ps
```

More commands can be found in the appcli README [here](https://github.com/brightsparklabs/appcli)


