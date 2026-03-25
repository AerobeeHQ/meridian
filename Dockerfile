# Codex - Adobe Analytics Configuration Viewer
FROM python:3.13-slim

# Build arguments for git info (passed from docker-compose or CI)
ARG GIT_BRANCH=unknown
ARG GIT_COMMIT=unknown

WORKDIR /app

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# uv settings: copy mode avoids hardlink issues in Docker's layered filesystem
ENV UV_LINK_MODE=copy

# Install dependencies (cached layer - only rebuilds when lock/pyproject change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

# Copy application code
COPY app/ app/
COPY exports/ exports/
COPY config.json config.json
COPY run.py run.py

# Generate git info file for runtime
RUN echo "branch=${GIT_BRANCH}" > git_info.txt && \
    echo "commit=${GIT_COMMIT}" >> git_info.txt

# Create directories
RUN mkdir -p cache exports

# Expose port
EXPOSE 5010

ENV HOST=0.0.0.0

CMD ["uv", "run", "run.py"]
