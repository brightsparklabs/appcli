##
 # Makefile
 # ______________________________________________________________________________
 #
 # Created by brightSPARK Labs
 # www.brightsparklabs.com
 ##

.PHONY: help init test lint format

VENV_NAME?=.venv
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=${VENV_NAME}/bin/python
APP_VERSION=$(shell git describe --always --dirty)

.DEFAULT: help
help:
	@echo "make test"
	@echo "       run tests"
	@echo "make lint"
	@echo "       run flake8"
	@echo "make isort"
	@echo "       run + apply isort"
	@echo "make isort-check"
	@echo "       check with isort"
	@echo "make format"
	@echo "       run + apply black"
	@echo "make format-check"
	@echo "       check with black"
	@echo "make build-wheel"
	@echo "       build wheel"
	@echo "make publish-wheel"
	@echo "       publish wheel"
	@echo "make all"
	@echo "       run format + isort + lint + test"
	@echo "make docker"
	@echo "       build docker image"
	@echo "make docker-publish"
	@echo "       publish docker image"
	@echo "make check"
	@echo "       run format-check + isort-check + lint + test"

# Requirements are in setup.py, so whenever setup.py is changed, re-run installation of dependencies.
venv: $(VENV_NAME)/bin/activate
$(VENV_NAME)/bin/activate: setup.py
	test -d $(VENV_NAME) || python -m venv $(VENV_NAME)
	${PYTHON} -m pip install -U pip
	${PYTHON} -m pip install -e .
	${PYTHON} -m pip install -e '.[dev]'
	touch $(VENV_NAME)/bin/activate

test: venv
	${PYTHON} -m pytest

lint: venv
	${PYTHON} -m flake8 --ignore=E501,W503 --exclude=appcli/__init__.py appcli tests

isort: venv
	${PYTHON} -m isort .

isort-check: venv
	${PYTHON} -m isort . --diff --check-only

format: venv
	${PYTHON} -m black .

format-check: venv
	${PYTHON} -m black . --diff --check

build-wheel: venv
	${PYTHON} -m pip install setuptools wheel twine
	${PYTHON} setup.py sdist bdist_wheel

publish-wheel: build-wheel
	twine upload dist/*

docker:
	docker build -t brightsparklabs/appcli:${APP_VERSION} -t brightsparklabs/appcli:latest .

docker-publish: docker
	docker push brightsparklabs/appcli:${APP_VERSION}
	docker push brightsparklabs/appcli:latest

all: format isort lint test

check: format-check isort-check lint test