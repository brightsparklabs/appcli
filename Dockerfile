##
 # The build file for creating appcli images.
 #
 # This file is broken up into 3 sections:
 # - Base Layer
 #      An extensible image which adds all dependencies needed to run appcli.
 # - Build Layers
 #      Intermediate images that download the executables for each orchestrator.
 # - Orchestrator Layers.
 #      Final layers that extend the `base` layer but pull in the executables for the given orchestrator.
 #
 # To build the `docker-compose` orchestrated appcli image for example:
 #      docker build --target appcli-docker-compose \
 #          -t brightsparklabs/appcli-docker-compose:${APP_VERSION} \
 #          -t brightsparklabs/appcli-docker-compose:latest .
 # _____________________________________________________________________________
 #
 # Created by brightSPARK Labs
 # www.brightsparklabs.com
 ##


# -----------------------------------------------------------------------------
# BASE LAYER
# -----------------------------------------------------------------------------

FROM python:3.12.3-slim-bullseye AS appcli-base

ENV LANG=C.UTF-8

RUN \
    # set timezone to UTC by default
    ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime \
    # use unicode
    && locale-gen C.UTF-8 || true \
    # make Apt non-interactive
    && echo 'APT::Get::Assume-Yes "true";' > /etc/apt/apt.conf.d/90appcli \
    && echo 'DPkg::Options "--force-confnew";' >> /etc/apt/apt.conf.d/90appcli \
    # prepare for docker install
    && apt-get update \
    && apt-get -y install --no-install-recommends \
        git \
        vim-tiny \
    && apt-get -y autoremove \
    && apt-get -y clean \
    && rm -rf /var/lib/apt/lists/* \
    # Git has recently added more strict requirements for directory ownership
    # of Git managed directories. This has caused issues with updating to new
    # releases as the '/conf' directory is managed by Git. To address this
    # ownership issue, we can define directories as safe in the git config
    # settings. Currently, it does not support defining directories in the
    # following way: '/opt/brightsparklabs/*'. Instead, we have to define
    # all directories as safe, which given this is only within the context
    # of a docker image, is acceptable. In future, when the above means of
    # defining safe directories is added, we should update this command to
    # be more explicit around what directories should be considered safe.
    && git config --system --add safe.directory '*'


# -----------------------------------------------------------------------------
# BUILD LAYERS
# -----------------------------------------------------------------------------

FROM alpine:3.15.0 AS docker-compose-builder
WORKDIR /tmp

# Docker
# https://docs.docker.com/engine/release-notes/26.0/
ARG DOCKER_VERSION=26.0.2

# Docker Compose
# https://docs.docker.com/compose/release-notes/
ARG DOCKER_COMPOSE_VERSION=2.27.0

# Download binaries.
RUN \
    wget -q https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz \
    && tar xf docker-${DOCKER_VERSION}.tgz \
    && wget -q https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64 \
    && wget -q https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64.sha256 \
    && sha256sum -c docker-compose-linux-x86_64.sha256 \
    && chmod +x docker-compose-linux-x86_64

# -----------------------------------------------------------------------------

FROM alpine:3.15.0 AS helm-builder
WORKDIR /tmp

# Kubectl
# https://dl.k8s.io/release/stable.txt
ARG KUBECTL_VERSION=1.30.0

# Helm
# https://github.com/helm/helm/releases
ARG HELM_VERSION=3.14.4

# K9S
# https://github.com/derailed/k9s/releases
ARG K9S_VERSION=0.32.4

# Download binaries.
RUN \
    wget -q https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl \
    && chmod 0755 kubectl \
    && wget -q https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz \
    && wget -q https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz.sha256sum \
    && sha256sum -c helm-v${HELM_VERSION}-linux-amd64.tar.gz.sha256sum  \
    && tar -xf helm-v${HELM_VERSION}-linux-amd64.tar.gz \
    && wget -q https://github.com/derailed/k9s/releases/download/v${K9S_VERSION}/k9s_Linux_amd64.tar.gz \
    && tar -xf k9s_Linux_amd64.tar.gz


# -----------------------------------------------------------------------------
# ORCHESTRATOR LAYERS
# -----------------------------------------------------------------------------

FROM appcli-base AS appcli-docker-compose

COPY --from=docker-compose-builder /tmp/docker/docker /usr/bin
COPY --from=docker-compose-builder /tmp/docker-compose-linux-x86_64 /usr/local/lib/docker/cli-plugins/docker-compose

FROM appcli-base AS appcli-helm

COPY --from=helm-builder /tmp/kubectl /usr/bin/
COPY --from=helm-builder /tmp/linux-amd64/helm /usr/bin
COPY --from=helm-builder /tmp/k9s /usr/bin/