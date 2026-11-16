.DEFAULT_GOAL := help

VENV        := $(CURDIR)/.venv
PY          := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
FLASK       := $(VENV)/bin/flask

INFRA       := mongodb kafka mongo-express kafka-ui

# Host-side settings (Kafka needs the HOST listener on 29092 in docker-compose.yml)
export KAFKA_BROKER ?= localhost:29092
export MONGO_URI    ?= mongodb://localhost:27017/

.PHONY: help venv install infra infra-down api seed worker up down stop start restart build rebuild logs ps clean nuke

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

## ---- Dev workflow (infra in Docker, code on host) ----

venv: ## Create the virtualenv
	python3 -m venv $(VENV)

install: venv ## Install Python dependencies
	$(PIP) install -r api/requirements.txt -r worker/requirements.txt

infra: ## Start only MongoDB, Kafka and their UIs
	docker compose up -d $(INFRA)

infra-down: ## Stop the infra containers (keeps data)
	docker compose stop $(INFRA)

api: ## Run Flask API locally with auto-reload
	cd api && $(FLASK) --debug run

seed: ## Seed the products collection (needs `make infra` running)
	cd api && $(PY) bootstrap/db-init.py

worker: ## Run the worker locally
	cd worker && $(PY) worker.py

## ---- Full Docker stack ----

up: ## Build and start everything in Docker
	docker compose up -d --build

down: ## Stop and remove containers (keeps data)
	docker compose down

stop: ## Stop containers without removing them
	docker compose stop

start: ## Start previously stopped containers
	docker compose start

restart: ## Restart all containers
	docker compose restart

build: ## Build images
	docker compose build

rebuild: ## Rebuild and restart one service: make rebuild s=flask-api
	docker compose up -d --build $(s)

logs: ## Follow logs (all, or: make logs s=order-worker)
	docker compose logs -f $(s)

ps: ## List running services
	docker compose ps

## ---- Cleanup ----

clean: ## Remove __pycache__ folders
	find . -path ./.venv -prune -o -name __pycache__ -type d -exec rm -rf {} +

nuke: ## DANGER: remove containers AND volumes (wipes Mongo/Kafka data)
	@read -p "This deletes all Mongo and Kafka data. Continue? [y/N] " a; \
	if [ "$$a" = "y" ]; then docker compose down -v; else echo "Aborted."; fi
