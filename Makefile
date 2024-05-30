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
# Format and linter rules to ignore.
# See https://docs.astral.sh/ruff/rules/
RULES=E731

.DEFAULT: help
help:
	@echo "make test"
	@echo "       run tests"
	@echo "make lint"
	@echo "       run ruff check"
	@echo "make lint-check"
	@echo "       dry-run ruff check"
	@echo "make format"
	@echo "       run ruff format"
	@echo "make format-check"
	@echo "       dry-run ruff format"
	@echo "make build-wheel"
	@echo "       build wheel"
	@echo "make publish-wheel"
	@echo "       publish wheel"
	@echo "make all"
	@echo "       run format + lint + test"
	@echo "make docker"
	@echo "       build docker image"
	@echo "make docker-publish"
	@echo "       publish docker image"
	@echo "make check"
	@echo "       run format-check + lint-check + test"
	@echo "make precommit"
	@echo "       manually trigger precommit hooks"

# Requirements are in setup.py, so whenever setup.py is changed, re-run installation of dependencies.
venv: $(VENV_NAME)/bin/activate
$(VENV_NAME)/bin/activate: setup.py .github/.pre-commit-config.yaml
	test -d $(VENV_NAME) || python -m venv $(VENV_NAME)
	${PYTHON} -m pip install -U pip
	${PYTHON} -m pip install -e .
	${PYTHON} -m pip install -e '.[dev]'
	${PYTHON} ${VENV_NAME}/bin/pre-commit install --config .github/.pre-commit-config.yaml
	touch $(VENV_NAME)/bin/activate

test: venv
	${PYTHON} -m pytest

lint: venv
# Ignore lambda functions in `appcli/models/configuration.py::Hooks`.
	${PYTHON} -m ruff check --fix --ignore ${RULES} .

lint-check: venv
	${PYTHON} -m ruff check --ignore ${RULES} .

format: venv
	${PYTHON} -m ruff format .

format-check: venv
	${PYTHON} -m ruff format --check .

clean:
	rm -rf build/ dist/ bsl_appcli.egg-info/

build-wheel: venv clean
	${PYTHON} -m pip install setuptools wheel twine
	${PYTHON} setup.py sdist bdist_wheel

publish-wheel: build-wheel
	${PYTHON} -m twine check dist/*
	${PYTHON} -m twine upload --non-interactive --username __token__ --password ${PYPI_TOKEN} dist/*

publish-wheel-test: build-wheel
	${PYTHON} -m twine check dist/*
	${PYTHON} -m twine upload --repository-url https://test.pypi.org/legacy/ --non-interactive --username __token__ --password ${PYPI_TOKEN} dist/*

# NOTE: We want to build and push the `brightsparklabs/appcli-docker-compose` image as 
# `brightsparklabs/appcli` as well, to support legacy projects that use it. 
docker:
	docker build --target appcli-docker-compose \
		-t brightsparklabs/appcli-docker-compose:${APP_VERSION} \
		-t brightsparklabs/appcli-docker-compose:latest .
	docker build --target appcli-helm \
		-t brightsparklabs/appcli-helm:${APP_VERSION} \
		-t brightsparklabs/appcli-helm:latest .
	docker build --target appcli-docker-compose \
		-t brightsparklabs/appcli:${APP_VERSION} \
		-t brightsparklabs/appcli:latest .

docker-publish: docker
	docker push brightsparklabs/appcli-docker-compose:${APP_VERSION}
	docker push brightsparklabs/appcli-docker-compose:latest
	docker push brightsparklabs/appcli-helm:${APP_VERSION}
	docker push brightsparklabs/appcli-helm:latest
	docker push brightsparklabs/appcli:${APP_VERSION}
	docker push brightsparklabs/appcli:latest

all: format lint test

check: format-check lint-check test

precommit: venv
	$(VENV_NAME)/bin/pre-commit run -c .github/.pre-commit-config.yaml