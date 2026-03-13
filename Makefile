# Codex Makefile
#
# Usage:
#   make up                              # Build and start (current branch)
#   make deploy BRANCH=main              # Switch to branch, pull, rebuild
#   make deploy BRANCH=feature/xyz       # Switch to feature branch, pull, rebuild
#   make down                            # Stop containers
#   make logs                            # View logs
#
# One-liner alternative (for command history):
#   git fetch && git switch main && git pull && make up

GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

.PHONY: build up down logs restart deploy

build:
	@echo "Building with $(GIT_BRANCH)@$(GIT_COMMIT)"
	GIT_BRANCH=$(GIT_BRANCH) GIT_COMMIT=$(GIT_COMMIT) docker compose build

up: build
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart: down up

# Deploy a specific branch: make deploy BRANCH=main
deploy:
ifndef BRANCH
	$(error BRANCH is required. Usage: make deploy BRANCH=main)
endif
	@echo "Deploying branch: $(BRANCH)"
	git fetch
	git switch $(BRANCH)
	git pull
	$(MAKE) restart

