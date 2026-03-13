# Issue 009: Git Build Info in Footer

**Date:** March 13, 2026  
**Type:** Feature  
**Status:** Completed  
**Branch:** `main`

## Objective

Add git branch name and commit hash to the application footer to easily identify which build is being previewed, both in local development and Docker deployments.

## Problem Statement

When testing different branches or deployments, there was no easy way to verify which code version was running in the browser. This made it difficult to:
- Confirm a deployment was successful
- Verify which branch was deployed to a test environment
- Debug issues by correlating with specific commits

## Solution

### Dual-Source Git Info

The solution retrieves git info from two sources depending on the environment:

1. **Local Development**: Uses `subprocess` to run `git rev-parse` commands directly
2. **Docker Containers**: Reads from `git_info.txt` file generated at build time

### Files Created

1. **`app/services/git_info.py`** - Git information utility module
   - `get_git_info()` returns branch, short commit, and full commit hash
   - Falls back to `git_info.txt` when `.git` folder unavailable
   - Graceful handling when git info is unavailable

2. **`docker-build.sh`** - Helper script for Docker builds
   - Extracts git branch and commit from local repo
   - Exports as environment variables for docker-compose
   - Provides build feedback

### Files Modified

1. **`app/__init__.py`**
   - Import `get_git_info` from services
   - Add `GIT_BRANCH` and `GIT_COMMIT` to app config

2. **`app/routes/main.py`**
   - Added `inject_git_info()` context processor
   - Automatically injects `git_branch` and `git_commit` to all templates

3. **`app/templates/base.html`**
   - Footer now displays: `Build: branch@commit`
   - Added pipe separators between footer items for readability

4. **`Dockerfile`**
   - Added `GIT_BRANCH` and `GIT_COMMIT` build arguments
   - Generates `git_info.txt` during image build

5. **`docker-compose.yml`**
   - Updated build section to pass git args
   - Uses environment variable fallback: `${GIT_BRANCH:-unknown}`

## Usage

### Local Development

No action needed - git info is retrieved automatically via subprocess.

### Docker Deployment

**Option 1: Using helper script (recommended)**
```bash
./docker-build.sh
docker compose up -d
```

**Option 2: Manual with environment variables**
```bash
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
export GIT_COMMIT=$(git rev-parse --short HEAD)
docker compose up -d --build
```

**Option 3: Direct build args**
```bash
docker build --build-arg GIT_BRANCH=main --build-arg GIT_COMMIT=abc1234 -t codex .
```

## Footer Display Format

The footer now shows:
```
Report Suite: rsid_example | Cached: 2026-03-13 10:30:00 | Age: 5 minutes | Build: main@9e580f2
```

## Technical Notes

- Short commit hash is 7 characters (standard git abbreviation)
- If git info unavailable, displays `Build: unknown`
- Context processor approach avoids modifying every route individually
- `git_info.txt` format: simple key=value pairs for easy parsing

