##
 # Makefile
 # ______________________________________________________________________________
 #
 # Created by brightSPARK Labs
 # www.brightsparklabs.com
 ##

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

# Warn whenever make sees a reference to an undefined variable.
MAKEFLAGS += --warn-undefined-variables
# Disable implicit rules as they were not designed for python.
MAKEFLAGS += --no-builtin-rules
# Set the shell to `bash` to give better error messaging/handling.
# See https://stackoverflow.com/questions/20615217/bash-bad-substitution
SHELL := /bin/bash

VENV_NAME?=.venv
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON_EXEC=${VENV_NAME}/bin/python
PYTHON_VERSION=3.12.3
APP_VERSION=$(shell git describe --always --dirty)
# Format and linter rules to ignore.
# See https://docs.astral.sh/ruff/rules/
# Ignore lambda functions in `appcli/models/configuration.py::Hooks`.
RULES=E731


# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------

# The below `awk` is a simple variation for self-documenting Makefiles. See:
# https://michaelgoerz.net/notes/self-documenting-makefiles.html
#
# Basically this allows task documentation to be appended to the task name
# with two hashes and it will be picked up in help output.
.DEFAULT_GOAL := help
.PHONY: help
help: ## Display this help section.
	@grep -E '^([a-zA-Z0-9_-]+):.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "%-20s %s\n", $$1, $$2}'

# Requirements are in setup.py, so whenever setup.py is changed, re-run installation of dependencies.
.PHONY: venv
venv: $(VENV_NAME)/bin/activate ## Build the virtual environment.
$(VENV_NAME)/bin/activate: setup.py .github/.pre-commit-config.yaml
	test -d $(VENV_NAME) || uv venv --python ${PYTHON_VERSION} ${VENV_NAME}
	uv pip install -e .
	uv pip install -e '.[dev]'
	${PYTHON_EXEC} ${VENV_NAME}/bin/pre-commit install --config .github/.pre-commit-config.yaml
	touch $(VENV_NAME)/bin/activate

.PHONY: test
test: venv ## Run unit tests.
	${PYTHON_EXEC} -m pytest

.PHONY: lint
lint: venv ## Lint the codebase.
	${PYTHON_EXEC} -m ruff check --fix --ignore ${RULES} .

.PHONY: lint-check
lint-check: venv ## Lint the codebase (dryrun).
	${PYTHON_EXEC} -m ruff check --ignore ${RULES} .

.PHONY: format
format: venv ## Format the codebase.
	${PYTHON_EXEC} -m ruff format .

.PHONY: format-check
format-check: venv ## Format the codebase (dryrun).
	${PYTHON_EXEC} -m ruff format --check .

.PHONY: clean
clean: ## Remove the build artifacts.
	rm -rf build/ dist/ bsl_appcli.egg-info/ .venv/

.PHONY: build-wheel
build-wheel: venv clean ## Build the python package.
	uv pip install setuptools wheel twine
	${PYTHON_EXEC} setup.py sdist bdist_wheel

.PHONY: publish-wheel
publish-wheel: build-wheel ## Publish the python package.
	${PYTHON_EXEC} -m twine check dist/*
	${PYTHON_EXEC} -m twine upload --non-interactive --username __token__ --password ${PYPI_TOKEN} dist/*

.PHONY: publish-wheel-test
publish-wheel-test: build-wheel ## Test publish the python package.
	${PYTHON_EXEC} -m twine check dist/*
	${PYTHON_EXEC} -m twine upload --repository-url https://test.pypi.org/legacy/ --non-interactive --username __token__ --password ${PYPI_TOKEN} dist/*

# NOTE: We want to build and push the `brightsparklabs/appcli-docker-compose` image as 
# `brightsparklabs/appcli` as well, to support legacy projects that use it. 
.PHONY: docker
docker: ## Build the docker images.
	docker build --target appcli-docker-compose \
		-t brightsparklabs/appcli-docker-compose:${APP_VERSION} \
		-t brightsparklabs/appcli-docker-compose:latest .
	docker build --target appcli-helm \
		-t brightsparklabs/appcli-helm:${APP_VERSION} \
		-t brightsparklabs/appcli-helm:latest .
	docker build --target appcli-docker-compose \
		-t brightsparklabs/appcli:${APP_VERSION} \
		-t brightsparklabs/appcli:latest .

.PHONY: docker-publish
docker-publish: docker ## Publish all the docker images.
	docker push brightsparklabs/appcli-docker-compose:${APP_VERSION}
	docker push brightsparklabs/appcli-docker-compose:latest
	docker push brightsparklabs/appcli-helm:${APP_VERSION}
	docker push brightsparklabs/appcli-helm:latest
	docker push brightsparklabs/appcli:${APP_VERSION}
	docker push brightsparklabs/appcli:latest

.PHONY: all
all: format lint test ## Format, lint and test the codebase.

.PHONY: check
check: format-check lint-check test ## Format (dryrun), lint (dryrun) and test the codebase.

.PHONY: precommit
precommit: venv ## Run pre commit hooks.
	$(VENV_NAME)/bin/pre-commit run -c .github/.pre-commit-config.yaml