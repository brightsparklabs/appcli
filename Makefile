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

.DEFAULT: help
help:
	@echo "make test"
	@echo "       run tests"
	@echo "make lint"
	@echo "       run flake8"
	@echo "make format"
	@echo "       run black"
	@echo "make all"
	@echo "       run all the above"
	@echo "make isort"
	@echo "       run isort"

# Requirements are in setup.py, so whenever setup.py is changed, re-run installation of dependencies.
venv: $(VENV_NAME)/bin/activate
$(VENV_NAME)/bin/activate: setup.py
	test -d $(VENV_NAME) || ${PYTHON} -m venv $(VENV_NAME)
	${PYTHON} -m pip install -U pip
	${PYTHON} -m pip install -e .
	${PYTHON} -m pip install -e '.[dev]'
	touch $(VENV_NAME)/bin/activate

test: venv
	${PYTHON} -m pytest

lint: venv
	${PYTHON} -m flake8 --ignore=E501 --exclude=appcli/__init__.py appcli tests
	${PYTHON} -m isort -c || echo -e "\nReview isort errors with 'make isort'"

format: venv
	${PYTHON} -m black . || echo ha

isort: venv
	${PYTHON} -m isort

all: format test lint 

