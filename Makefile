-include ./backend/.env
export $(shell sed 's/=.*//' .env)
export REPOSITORY ?= ghcr.io/jslecointre
export NAME ?= pulsegraph
export VERSION ?= 0.0.1

# Tools
CONTAINER_CLI := docker
DOCKER_COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: run-services run-pulsegraph-be stop-containers build-base build-pulsegraph-be clean create-volumes logs info

.PHONY: clean docker push run

build-base:
	$(CONTAINER_CLI) build --platform linux/amd64 --no-cache -t $(REPOSITORY)/$(NAME)-base:$(VERSION) ./backend -f ./backend/Dockerfile-base --build-arg VERSION=${VERSION}


build-pulsegraph-be:
	$(CONTAINER_CLI) build --platform linux/amd64 --no-cache -t $(REPOSITORY)/$(NAME)-backend:$(VERSION) ./backend -f ./backend/Dockerfile --build-arg VERSION=${VERSION} --build-arg REGISTRY=${REPOSITORY}

tag-base:
	@echo "Determining previous version..."
	@PREV_VERSION=$$(echo $(VERSION) | awk -F. '{print $$1"."$$2"."$$3-1}') && \
	echo "Previous version: $$PREV_VERSION" && \
	echo "Fetching Image ID for $(REPOSITORY)/$(NAME)-base:$$PREV_VERSION..." && \
	IMAGE_ID=$$($(CONTAINER_CLI) images --filter "reference=$(REPOSITORY)/$(NAME)-base:$$PREV_VERSION" --format "{{.ID}}") && \
	if [ -n "$$IMAGE_ID" ]; then \
		echo "Image ID found: $$IMAGE_ID"; \
		echo "Tagging image $$IMAGE_ID as $(REPOSITORY)/$(NAME)-base:$(VERSION)"; \
		$(CONTAINER_CLI) tag $$IMAGE_ID $(REPOSITORY)/$(NAME)-base:$(VERSION); \
		echo "Successfully tagged $(REPOSITORY)/$(NAME)-base:$(VERSION)"; \
	else \
		echo "Error: No image found for $(REPOSITORY)/$(NAME)-base:$$PREV_VERSION"; \
		exit 1; \
	fi

push:
	$(CONTAINER_CLI) push $(REPOSITORY)/$(NAME)-backend:$(VERSION)


run-pulsegraph-be:
	@echo "Starting backend..."
	PROJECT_VERSION=${VERSION} REPOSITORY=${REPOSITORY} NAME=${NAME} $(DOCKER_COMPOSE) up -d backend
	@echo "Backend is now running."


run-services: create-volumes
	@echo "Starting services:"
	$(DOCKER_COMPOSE) up -d postgres  || \
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

create-volumes:
	@echo "Creating volume directories with correct permissions..."
	@mkdir -p ./volumes/postgres
	@chmod -R 777 ./volumes
	@echo "Volume directories created and permissions set."

logs:
	$(DOCKER_COMPOSE) logs -f
