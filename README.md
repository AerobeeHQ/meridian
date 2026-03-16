# Codex

### A Data Dictionary for your Adobe Analytics Report Suites

Codex provides **configuration intelligence** for Adobe Analytics, serving as a living data dictionary that documents your report suite implementation. It gives analysts, developers, and stakeholders a single source of truth for understanding how your Adobe Analytics data is structured and collected.

Converted from [RShiny SDR](https://github.com/Brontojoris/rshiny-sdr) to Python/Flask.

---

## Features

- **Conversion Variables (eVars)** — View all eVars with allocation, expiration, and descriptions
- **Traffic Variables (Props)** — Browse props with pathing and list support settings
- **Success Events** — List all events with type, serialisation, and descriptions
- **List Variables** — View ListVar configurations and delimiters
- **Processing Rules** — Display all processing rules with conditions and actions (API 1.4)
- **Marketing Channels** — Browse channel definitions and settings
- **Channel Rules** — View marketing channel classification rules
- **Detail Views** — Drill into individual dimensions/events for full configuration details
- **CSV Export** — Export any configuration table for documentation or audits
- **Caching** — JSON file-based caching (hourly expiry) to reduce API calls

---

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Adobe Analytics API credentials (see [Configuration](#configuration))

### Installation

```bash
# Clone the repository
git clone https://github.com/Brontojoris/Codex.git
cd Codex

# Install dependencies
uv sync

# Copy and configure settings
cp config.dist.json config.json
# Edit config.json with your credentials
```

### Running the Application

```bash
# Start the Flask development server
uv run run.py

# Default: http://127.0.0.1:5010
# Custom port: PORT=5011 uv run run.py
```

### Health Check

```bash
# Verify setup (checks config, directories, imports)
uv run verify_setup.py
```

---

## Configuration

Create a `config.json` file in the project root (use `config.dist.json` as a template).

### Required Settings

| Key | Description |
|-----|-------------|
| `APP_TITLE` | Name displayed in the header (e.g., "Company Name") |
| `AW_REPORTSUITE_ID` | Your Adobe Analytics report suite ID |

### API 2.0 (OAuth2) — Recommended

| Key | Description |
|-----|-------------|
| `API_VERSION` | Set to `"2.0"` |
| `CLIENT_ID` | OAuth2 Client ID from Adobe I/O Console |
| `CLIENT_SECRET` | OAuth2 Client Secret |
| `ORGANIZATION_ID` | Your Adobe Org ID (e.g., `ABC123@AdobeOrg`) |
| `SCOPES` | OAuth2 scopes (optional, has sensible defaults) |

### API 1.4 (WSSE) — Legacy

| Key | Description |
|-----|-------------|
| `AW_USERNAME` | WSSE username (format: `username:company`) |
| `AW_SECRET` | WSSE shared secret |

> **Note:** Even when using API 2.0, WSSE credentials are still required for certain endpoints that haven't been migrated to 2.0 (e.g., Processing Rules).

### Example Configuration

```json
{
    "APP_TITLE": "Acme Corp",
    "AW_REPORTSUITE_ID": "acmeprod",
    "API_VERSION": "2.0",
    "CLIENT_ID": "your-client-id",
    "CLIENT_SECRET": "your-client-secret",
    "ORGANIZATION_ID": "ABC123@AdobeOrg",
    "AW_USERNAME": "user:acme",
    "AW_SECRET": "wsse-secret"
}
```

---

## Authentication

Codex uses a **hybrid API approach**:

- **API 2.0 (OAuth2)** — Primary method for most endpoints (eVars, Props, Events, ListVars, Marketing Channels). OAuth2 credentials are obtained from the [Adobe I/O Console](https://console.adobe.io/).

- **API 1.4 (WSSE)** — Legacy method required for endpoints not yet available in API 2.0 (Processing Rules). WSSE credentials can be obtained from Admin → User Management → Users in Adobe Analytics.

---

## Docker

```bash
# Build and run
docker compose up -d --build

# View logs
docker compose logs -f
```

> **Important:** Ensure the exports directory is mounted with read-write permissions (`:rw`) in your `docker-compose.yml`.

---

## Project Structure

```
Codex/
├── app/
│   ├── routes/          # Flask route handlers
│   ├── services/        # API wrappers and business logic
│   │   ├── adobe_analytics_v2.py   # API 2.0 client (OAuth2)
│   │   ├── adobe_analytics.py      # API 1.4 client (WSSE)
│   │   ├── adobe_auth.py           # OAuth2 token management
│   │   └── cache.py                # JSON file-based caching
│   └── templates/       # Jinja2 HTML templates
├── cache/               # Cached API responses (git-ignored)
├── exports/             # CSV exports directory
├── notebooks/           # Jupyter notebooks for API exploration
├── docs/                # Documentation and post-mortems
└── assets/              # Images and screenshots
```

---

## Live Demo

[https://codex.maxisdev.com](https://codex.maxisdev.com)

![Homepage screenshot](./assets/screenshots/codex-live-demo.png)

---

## Tools

- **IDE:** [PyCharm 2025.3](https://www.jetbrains.com/pycharm/)
- **Python:** 3.13+
- **Package Manager:** [uv](https://docs.astral.sh/uv/)

---

## License

MIT

---

*Last updated: March 2026*
