# AI Agent & Copilot Guide for Codex

## 1. Project Context
**Codex** is a Python/Flask application that visualizes Adobe Analytics configurations (eVars, Props, Events, processing rules, marketing channel settings). It is a port of [RShiny SDR](https://github.com/Brontojoris/rshiny-sdr).

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
  - *Testing*: Currently there is only **Manual testing**. No unit tests. Reliant on `verify_setup.py`. Devise a testing strategy that is **fast and reliable**.

## 4. Critical Workflows
- **Install/Sync**: `uv sync`.
- **Startup**: `uv run run.py` (Default: http://127.0.0.1:5010).
- **Health Check**: `uv run verify_setup.py` (checks config, directories, imports).
- **Docker**: `docker compose up -d --build`.
- **Config**: `config.json` (git-ignored). Template: `config.dist.json`.
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

## 6. Review & Preview

After completing a feature implementation, or whenever the user needs to review changes visually:

1. **Check if the app is already running** on port 5010:
   ```bash
   curl -s http://127.0.0.1:5010 > /dev/null && echo "running" || echo "stopped"
   ```
2. **If not running**, start it bound to all interfaces so it's reachable over Tailscale:
   ```bash
   HOST=0.0.0.0 uv run run.py > /tmp/codex.log 2>&1 &
   sleep 3 && curl -s http://127.0.0.1:5010 > /dev/null && echo "UP"
   ```
3. **Always present the review link** as a clickable markdown hyperlink:
   ```
   [http://100.78.114.119:5010](http://100.78.114.119:5010)
   ```

**Tailscale IP**: `100.78.114.119` — this container's stable Tailscale address.
The app must be started with `HOST=0.0.0.0` to be reachable via Tailscale (default binds to `127.0.0.1` only).

## 7. Key Files
- `app/routes/main.py`: Core application logic.
- `app/services/adobe_analytics_v2.py`: API 2.0 wrapper.
- `app/services/adobe_analytics.py`: API 1.4 wrapper.
- `app/services/adobe_auth.py`: OAuth2 token management.
- `app/services/cache.py`: JSON file-based caching with per-key TTL.
- `app/services/cache_warmer.py`: Background cache pre-warming via APScheduler (24h interval).
- `app/services/notes.py`: User-provided dimension annotation storage (JSON file-based).
- `verify_setup.py`: Local setup and configuration checks.
- `notebooks/`: Exploratory scripts.
