# BSL Application CLI Library

A library for adding CLI interfaces to applications in the brightSPARK Labs
style.

# Development

This section details how to build/test/run/debug the system in a development
environment.

## Prerequisites

The following must be installed and in the `PATH`:

- java
- docker

## Build

    ./gradlew build

## Test

### Unit Tests

    ./gradlew test

### Integration Tests

    ./gradlew integrationTest

## Install

    ./gradlew devInstall

## Usage

### Configure System

    /opt/brightsparklabs/{{REPO_NAME}}/current/{{REPO_NAME}} configure

### Start System

    /opt/brightsparklabs/{{REPO_NAME}}/current/{{REPO_NAME}} stop

### Interact

**TBD**

### Shutdown System

    /opt/brightsparklabs/{{REPO_NAME}}/current/{{REPO_NAME}} stop

# Deployment

This section details how to build a release for deployment and how to
install/run it on a Production system.

## Prerequisites

The following must be installed and in the `PATH`:

- docker

## Create Release

    ./gradlew releasePack

## Install

    ./<installer>.sh

## Usage

### Configure System

    /opt/brightsparklabs/{{REPO_NAME}}/current/{{REPO_NAME}} configure

### Start System

    /opt/brightsparklabs/{{REPO_NAME}}/current/{{REPO_NAME}} start

### Interact

**TBD**

### Shutdown System

    /opt/brightsparklabs/{{REPO_NAME}}/current/{{REPO_NAME}} stop

# Licenses

Refer to the `LICENSE` file for details.

This project makes use of several libraries and frameworks. Refer to the
`LICENSES` folder for details.

