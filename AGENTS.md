# AI Agent & Copilot Guide for Codex

## 1. Project Context
**Codex** is a Python/Flask application that visualizes Adobe Analytics configurations (eVars, Props, Events). It is a port of [RShiny SDR](https://github.com/Brontojoris/rshiny-sdr), aiming for **MVP velocity**.

## 2. Architecture & Tech Stack
- **Framework**: Flask (`app/routes/`, `app/templates/`).
- **Data Source**: Adobe Analytics API 1.4 via **WSSE Authentication**.
- **Service Layer**:
  - `app/services/adobe_analytics.py`: Custom raw HTTP client. **Manually constructs X-WSSE header**.
  - `app/services/cache.py`: JSON file-based caching (hourly expiry).
- **Frontend**: Server-side rendered Jinja2 templates.
- **Dependencies**: `pandas`, `ipyleaflet`. Python 3.13+.

## 3. User & Developer Context (Crucial)
- **User Profile**: Strong JavaScript background, **Beginner in Python**.
  - *Action*: Explain Python concepts clearly. Avoid overly "pythonic" code if a JS-style approach is readable.
- **Philosophy**: **MVP Velocity**. Speed over perfection. Code is disposable.
  - *Testing*: **Manual testing only**. No unit tests. Reliant on `verify_setup.py`.

## 4. Critical Workflows
- **Startup**: `python run.py` (Default: http://127.0.0.1:5010).
- **Health Check**: `python verify_setup.py` (Checks config, directories, imports).
- **Docker**: `docker compose up -d --build`.
- **Config**: `config.json` (git-ignored). Template: `config.dist.json`.
  - Required: `AW_USERNAME`, `AW_SECRET`, `AW_REPORTSUITE_ID`.

## 5. Coding & Implementation Guidelines
- **API Requests**:
  - **Always** wrap calls with cache: `cache.get_or_set(rsid, key, fetch_function)`.
  - Use `AdobeAnalyticsService` for all 1.4 API calls.
- **New Features**:
  1. Add Service method (`app/services/adobe_analytics.py`).
  2. Add Route (`app/routes/main.py`) with Caching.
  3. Add Template (`app/templates/`).
- **Jupyter Notebooks**:
  - **NEVER** edit `.ipynb` JSON directly.
  - Provide code snippets to copy/paste into cells.
- **Security**:
  - Never log credentials. Ensure `exports/` is writable.

## 6. Key Files
- `app/routes/main.py`: Core application logic.
- `app/services/adobe_analytics.py`: API Wrapper & Authentication.
- `notebooks/`: Exploratory scripts.

