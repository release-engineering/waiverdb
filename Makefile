# Use podman-compose by default if available.
ifeq (, $(shell which podman-compose))
    COMPOSE := docker-compose
    PODMAN := docker
else
    COMPOSE := podman-compose
    PODMAN := podman
endif

BROWSER := xdg-open
SERVICE := dev

PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest --color=yes
FLAKE8 := $(PYTHON) -m flake8
PYLINT := $(PYTHON) -m pylint

PYTEST_ARGS := tests

all: help

help:
	@echo 'Usage:'
	@echo
	@echo '  make up - starts containers in docker-compose environment'
	@echo
	@echo '  make down - stops containers in docker-compose environment'
	@echo
	@echo '  make build - builds container images for docker-compose environment'
	@echo
	@echo '  make recreate - recreates containers for docker-compose environment'
	@echo
	@echo '  make exec [CMD=".."] - executes command in dev container'
	@echo
	@echo '  make sudo [CMD=".."] - executes command in dev container under root user'
	@echo
	@echo 'Variables:'
	@echo
	@echo '  COMPOSE=docker-compose|podman-compose'
	@echo '    - docker-compose or podman-compose command'
	@echo '      (default is "podman-compose" if available)'
	@echo
	@echo '  PODMAN=docker|podman'
	@echo '    - docker or podman command'
	@echo '      (default is "podman" if "podman-compose" is available)'
	@echo
	@echo '  SERVICE={dev|waiverdb-db}'
	@echo '    - service for which to run `make exec` and similar (default is "dev")'
	@echo '      Example: make exec SERVICE=waiverdb-db CMD=flake8'

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

recreate:
	$(COMPOSE) up -d --force-recreate

exec:
	$(PODMAN) exec waiverdb_$(SERVICE)_1 bash -c '$(CMD)'

sudo:
	$(PODMAN) exec -u root waiverdb_$(SERVICE)_1 bash -c '$(CMD)'
