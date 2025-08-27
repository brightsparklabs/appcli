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
SHELL := bash

PYTHON_VERSION=3.12.3
APP_VERSION=$(shell git describe --always --dirty)
# As this is a python project, we want this to be PEP440 compliant.
APP_VERSION_PYTHON=$(shell echo "${APP_VERSION}" | sed -E 's/^v//; s/-([0-9]+)-g([0-9a-f]+)/.\1+\2/; s/-dirty/.dirty/')
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
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z\$$/]+.*:.*?##\s/ {printf "\033[36m%-38s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Requirements are in `pyproject.toml`, so whenever `pyproject.toml` is changed, re-run installation of dependencies.
.PHONY: venv
venv: .venv/bin/activate ## Build the virtual environment.
.venv/bin/activate: pyproject.toml .github/.pre-commit-config.yaml
	APP_VERSION=${APP_VERSION_PYTHON} uv sync --group dev --group build
	APP_VERSION=${APP_VERSION_PYTHON} uv run pre-commit install --config .github/.pre-commit-config.yaml
	touch .venv/bin/activate

.PHONY: test
test: venv ## Run unit tests.
	APP_VERSION=${APP_VERSION_PYTHON} uv run pytest \
		--cov-report term-missing:skip-covered --cov=appcli tests/

.PHONY: lint
lint: venv ## Lint the codebase.
	APP_VERSION=${APP_VERSION_PYTHON} uv run ruff check --fix --ignore ${RULES} .

.PHONY: lint-check
lint-check: venv ## Lint the codebase (dryrun).
	APP_VERSION=${APP_VERSION_PYTHON} uv run ruff check --ignore ${RULES} .

.PHONY: format
format: venv ## Format the codebase.
	APP_VERSION=${APP_VERSION_PYTHON} uv run ruff format .

.PHONY: format-check
format-check: venv ## Format the codebase (dryrun).
	APP_VERSION=${APP_VERSION_PYTHON} uv run ruff format --check .

.PHONY: clean
clean: ## Remove the build artifacts.
	rm -rf build/ dist/ bsl_appcli.egg-info/

.PHONY: build-wheel
build-wheel: venv clean ## Build the python package.
	APP_VERSION=${APP_VERSION_PYTHON} uv build --sdist --wheel

.PHONY: publish-wheel
publish-wheel: build-wheel ## Publish the python package.
	APP_VERSION=${APP_VERSION_PYTHON} uv run hatch publish \
		--yes --user __token__ --auth ${PYPI_TOKEN} dist/*

.PHONY: publish-wheel-test
publish-wheel-test: build-wheel ## Test publish the python package.
	APP_VERSION=${APP_VERSION_PYTHON} uv run hatch publish \
		--yes --user __token__ --auth ${PYPI_TOKEN} --repo https://test.pypi.org/legacy/ dist/*

.PHONY: docker
docker: ## Build the docker images.
	docker build --target appcli-docker-compose \
		-t brightsparklabs/appcli-docker-compose:${APP_VERSION} \
		-t brightsparklabs/appcli-docker-compose:latest .
	docker build --target appcli-helm \
		-t brightsparklabs/appcli-helm:${APP_VERSION} \
		-t brightsparklabs/appcli-helm:latest .
    # NOTE: We want to build and push the `brightsparklabs/appcli-docker-compose` image as 
    # `brightsparklabs/appcli` as well, to support legacy projects that use it. 
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
	APP_VERSION=${APP_VERSION_PYTHON} uv run pre-commit run -c .github/.pre-commit-config.yaml

.PHONY: scan
scan: venv ## Scan the code for vulnerabilities.
	APP_VERSION=${APP_VERSION_PYTHON} uv run bandit -r --severity-level medium appcli/

.PHONY: docs
docs: venv ## Generate documentation from the code.
	APP_VERSION=$(APP_VERSION_PYTHON) uv run pdoc -o ./build/docs appcli/
