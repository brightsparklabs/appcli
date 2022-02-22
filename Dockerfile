##
 # Example image for running appcli.
 # _____________________________________________________________________________
 #
 # Created by brightSPARK Labs
 # www.brightsparklabs.com
 ##

FROM alpine:3.15.0 AS docker-binary-download

WORKDIR /tmp

# Download and extract the static docker binary
RUN \
    wget -q https://download.docker.com/linux/static/stable/x86_64/docker-20.10.6.tgz \
    && tar xf docker-20.10.6.tgz

FROM python:3.10.2-slim-bullseye

ENV LANG=C.UTF-8

COPY --from=docker-binary-download /tmp/docker/docker /usr/bin

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
    && rm -rf /var/lib/apt/lists/*
