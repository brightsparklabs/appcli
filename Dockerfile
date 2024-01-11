##
 # Example image for running appcli.
 # _____________________________________________________________________________
 #
 # Created by brightSPARK Labs
 # www.brightsparklabs.com
 ##

FROM alpine:3.15.0 AS docker-binary-download

WORKDIR /tmp

# List required versions for docker and compose.
ENV DOCKER_VERSION=24.0.7
ENV DOCKER_COMPOSE_VERSION=2.23.3

# Download docker and compose.
RUN wget -q https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz \
    && tar xf docker-${DOCKER_VERSION}.tgz \
    && wget -q https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64 \
    && wget -q https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64.sha256 \
    && sha256sum -c docker-compose-linux-x86_64.sha256 \
    && chmod +x docker-compose-linux-x86_64

FROM python:3.10.2-slim-bullseye

ENV LANG=C.UTF-8

COPY --from=docker-binary-download /tmp/docker/docker /usr/bin
COPY --from=docker-binary-download /tmp/docker-compose-linux-x86_64 /usr/local/lib/docker/cli-plugins/docker-compose

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
    && git config --global --add safe.directory '*'
