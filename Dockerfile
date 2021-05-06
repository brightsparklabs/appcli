##
 # Example image for running appcli.
 # _____________________________________________________________________________
 #
 # Created by brightSPARK Labs
 # www.brightsparklabs.com
 ##

FROM python:3.8.2-slim-buster

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
    && rm -rf /var/lib/apt/lists/*
