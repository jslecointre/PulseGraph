# Include environment variables from .env file
-include .env
export $(shell sed 's/=.*//' .env)

# Set PYTHONPATH
export PYTHONPATH=$(pwd):$(pwd)/vectordbs:$(pwd)/backend

# Tools
CONTAINER_CLI := docker
DOCKER_COMPOSE := docker-compose

.DEFAULT_GOAL := help

.PHONY: run-services stop-containers clean create-volumes logs info help

# Helper function to check if containers are healthy
check_containers:
	@echo "Checking if required containers are running and healthy..."
	@if [ -z "$$(docker compose ps -q postgres)" ] || \
		[ -z "$$(docker compose ps -q mlflow-server)" ]; then \
		echo "Some containers are not running. Starting services..."; \
		$(MAKE) run-backend; \
		echo "Waiting for containers to be healthy..."; \
		sleep 10; \
	else \
		echo "All required containers are running."; \
	fi


run-services: create-volumes
	@echo "Starting services:"
	$(DOCKER_COMPOSE) up -d postgres minio createbuckets mlflow-server || \
	{ \
		echo "Failed to infra services"; \
		unhealthy_containers=$$($(CONTAINER_CLI) ps -f health=unhealthy -q); \
		if [ -n "$$unhealthy_containers" ]; then \
			echo "Logs from unhealthy containers:"; \
			for container in $$unhealthy_containers; do \
				echo "Container ID: $$container"; \
				$(CONTAINER_CLI) logs $$container; \
			done; \
		else \
			echo "No unhealthy containers found, checking for failed containers..."; \
			failed_containers=$$($(CONTAINER_CLI) ps -f status=exited -q); \
			if [ -n "$$failed_containers" ]; then \
				echo "Logs from failed containers:"; \
				for container in $$failed_containers; do \
					echo "Container ID: $$container"; \
					$(CONTAINER_CLI) logs $$container; \
				done; \
			else \
				echo "No failed containers found, showing logs for all services."; \
				$(DOCKER_COMPOSE) logs; \
			fi; \
		fi; \
		exit 1; \
	}

# Stop / clean
stop-containers:
	@echo "Stopping containers..."
	$(DOCKER_COMPOSE) down -v

clean: stop-containers
	@echo "Cleaning up existing containers and volumes..."
	-@$(CONTAINER_CLI) pod rm -f $$($(CONTAINER_CLI) pod ls -q) || true
	-@$(CONTAINER_CLI) rm -f $$($(CONTAINER_CLI) ps -aq) || true
	-@$(CONTAINER_CLI) volume prune -f || true
	-@$(CONTAINER_CLI) container prune -f || true
	rm -rf .pytest_cache .mypy_cache data volumes

# Service / reusable targets
create-volumes:
	@echo "Creating volume directories with correct permissions..."
	@mkdir -p ./volumes/postgres ./volumes/minio
	@chmod -R 777 ./volumes
	@echo "Volume directories created and permissions set."

logs:
	$(DOCKER_COMPOSE) logs -f
