#!/bin/bash
# Build Docker image with git info embedded
# Usage: ./docker-build.sh

set -e

# Get git info
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Building Codex Docker image..."
echo "  Branch: $GIT_BRANCH"
echo "  Commit: $GIT_COMMIT"

# Export for docker-compose
export GIT_BRANCH
export GIT_COMMIT

# Build with docker-compose
docker compose build

echo ""
echo "Build complete! Run 'docker compose up -d' to start."

