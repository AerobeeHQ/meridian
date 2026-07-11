# AI Agent & Copilot Guide for Meridian

## 1. Project Context
**Meridian** is a Python/Flask application that visualizes Adobe Analytics configurations (eVars, Props, Events, processing rules, marketing channel settings). It is a port of [RShiny SDR](https://github.com/Brontojoris/rshiny-sdr).

## 2. Architecture & Tech Stack
- **Framework**: Flask (`app/routes/`, `app/templates/`).
- **Data Source**: Hybrid Adobe Analytics APIs.
  - **API 2.0 (default)** via OAuth2 (`adobe_auth.py`, `adobe_analytics_v2.py`)
  - **API 1.4 (legacy)** via WSSE (`adobe_analytics.py`) for endpoints still unavailable in 2.0 (for example processing rules).
- **Service Layer**:
  - `app/services/adobe_analytics_v2.py`: OAuth2-backed Analytics 2.0 client.
  - `app/services/adobe_analytics.py`: Legacy 1.4 client. **Manually constructs X-WSSE header**.
  - `app/services/adobe_auth.py`: OAuth2 token acquisition and caching.
  - `app/services/cache.py`: JSON file-based caching (hourly expiry).
- **Frontend**: Server-side rendered Jinja2 templates.
- **Package/Env Management**: `uv` (`pyproject.toml`, `uv.lock`).
- **Runtime/Dependencies**: Python 3.13+, `flask`, `requests`.

## 3. User & Developer Context (Crucial)
- **User Profile**: Strong JavaScript background, **Beginner in Python**.
  - *Action*: Explain Python concepts clearly. Avoid overly "pythonic" code if a JS-style approach is readable.
- **Philosophy**: **Post MVP Velocity**. We are now working on version 2. There should be more emphasis on architechture and scaling for future enhancements. Watch for opportunities to refactor and simplify code.
  - *Testing*: A **pytest unit test suite** exists in `tests/` (129 tests, 6 modules, ~0.2s). See `docs/testing.md` for full details. Reliant on `verify_setup.py` for live environment checks.

## 4. Critical Workflows
- **Install/Sync**: `uv sync`.
- **Run Tests**: `uv run pytest` — must pass before any commit or PR.
- **Startup**: `MERIDIAN_SECRETS_DIR=$(pwd)/secrets uv run run.py` (Default: http://127.0.0.1:5010).
- **Health Check**: `MERIDIAN_SECRETS_DIR=$(pwd)/secrets uv run verify_setup.py` (checks config, directories, imports).
- **Docker**: `docker compose up -d --build`.
- **Config**: Per-client JSON files in `secrets/` (e.g. `secrets/maxis.json`). This directory is git-ignored. Set `MERIDIAN_SECRETS_DIR=$(pwd)/secrets` before running.
  - Always required: `APP_TITLE`, `AW_REPORTSUITE_ID`.
  - API 2.0 required: `API_VERSION=2.0`, `CLIENT_ID`, `CLIENT_SECRET`, `ORGANIZATION_ID` (and optional `SCOPES`).
  - API 1.4 required: `AW_USERNAME`, `AW_SECRET`.
  - Note: Even with `API_VERSION=2.0`, WSSE credentials are still needed for legacy 1.4-only routes.

## 5. Coding & Implementation Guidelines
- **API Requests**:
  - **Always** wrap calls with cache: `cache.get_or_set(rsid, key, fetch_function)`.
  - Use `AdobeAnalyticsV2Service` by default for 2.0-supported resources.
  - Use `AdobeAnalyticsService` (`get_api_service_v14`) for 1.4-only resources.
- **New Features**:
  1. Add Service method in the correct service (`adobe_analytics_v2.py` or `adobe_analytics.py`).
  2. Add Route (`app/routes/main.py`) with Caching.
  3. Add Template (`app/templates/`).
- **Jupyter Notebooks**:
  - **NEVER** edit `.ipynb` JSON directly.
  - Provide code snippets to copy/paste into cells.
- **Security**:
  - Never log credentials. Ensure `exports/` is writable.

## 6. Unit Testing

### Running the suite
```bash
uv run pytest          # all 129 tests
uv run pytest -v       # verbose output
uv run pytest --cov=app --cov-report=term-missing  # with coverage
```

### Rules
- **Before every PR**: run `uv run pytest` and confirm all tests pass. Do not open a PR with a failing test suite.
- **When adding or changing service-layer code**: add or update the corresponding tests in `tests/test_<module>.py`. Tests should cover new behaviour and any edge cases introduced.
- **Scope**: unit tests cover `app/services/` only — no Flask app context, no real API calls, no network. Use `tmp_path` for file I/O and `unittest.mock.patch` for external calls.
- See `docs/testing.md` for a full description of each test module and guidance on writing new tests.

## 7. Review & Preview

After completing a feature implementation, or whenever the user needs to review changes visually:

1. **Check if the app is already running** on port 5010:
   ```bash
   curl -s http://127.0.0.1:5010 > /dev/null && echo "running" || echo "stopped"
   ```
2. **If not running**, start it bound to all interfaces so it's reachable over Tailscale:
   ```bash
   MERIDIAN_SECRETS_DIR=$(pwd)/secrets HOST=0.0.0.0 uv run run.py > /tmp/meridian.log 2>&1 &
   sleep 3 && curl -s http://127.0.0.1:5010 > /dev/null && echo "UP"
   ```
3. **If the hostname of the computer is M4, then Always present the review link** as a clickable markdown hyperlink:
   ```
   [http://100.78.114.119:5010](http://100.78.114.119:5010)
   ```

  **Tailscale IP**: `100.78.114.119` — M4's stable Tailscale address.
  The app must be started with `HOST=0.0.0.0` to be reachable via Tailscale (default binds to `127.0.0.1` only).

4. At the conclusion of tasks, summarise the actions taken into a new file at `../docs/autopsies/<issue-number>.md` using existing files in the `./docs/autopsies/` folder as a template.

## 8. Key Files
- `app/routes/main.py`: Core application logic and routes.
- `app/routes/auth.py`: Authentication routes (login, callback, logout) for per-user OAuth.
- `app/services/adobe_analytics_v2.py`: API 2.0 wrapper.
- `app/services/adobe_analytics.py`: API 1.4 wrapper.
- `app/services/adobe_auth.py`: OAuth2 token management.
- `app/services/adobe_launch.py`: Adobe Experience Platform Tags (Reactor) API client for Launch integration.
- `app/services/cache.py`: JSON file-based caching with per-key TTL.
- `app/services/cache_warmer.py`: Background cache pre-warming via APScheduler (24h interval).
- `app/services/git_info.py`: Git branch/commit info for footer display.
- `app/services/notes.py`: User-provided dimension annotation storage (JSON file-based).
- `verify_setup.py`: Local setup and configuration checks.
- `notebooks/`: Exploratory scripts.
