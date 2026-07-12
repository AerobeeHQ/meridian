# Quick Start — Local Development

This guide walks a developer through running Meridian on their local machine from scratch.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.13+ | Check with `python --version` |
| [uv](https://docs.astral.sh/uv/) | latest | Fast Python package manager |
| Adobe Analytics access | — | API credentials from Adobe I/O Console |

### Install uv (if needed)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

---

## 1. Clone the Repository

```bash
git clone https://github.com/aerobeehq/meridian.git
cd meridian
```

---

## 2. Install Dependencies

```bash
uv sync
```

This creates a virtual environment and installs all Python dependencies from `uv.lock`. No need to run `pip install` or create a `venv` manually.

---

## 3. Set Up Credentials

Meridian uses a **secrets directory** — a folder containing one JSON file per client. This lets a single Meridian instance serve multiple Adobe Analytics clients without mixing credentials.

### 3a. Create the secrets directory

```bash
mkdir -p ~/secrets/meridian
```

You can use any path. The folder can be anywhere on your machine; it should **not** be inside the `meridian/` repository directory (to avoid accidental commits).

### 3b. Create a client config file

```bash
cp config.dist.json ~/secrets/meridian/acme.json
```

Name the file after your client or report suite (e.g. `acme.json`, `mycompany.json`). The filename stem becomes the client slug in URLs (`/acme/`, `/mycompany/`).

### 3c. Fill in your credentials

Open `~/secrets/meridian/acme.json` in your editor and fill in the required values:

```json
{
    "APP_TITLE": "Acme Corp",
    "AW_REPORTSUITE_ID": "acmeprod",
    "API_VERSION": "2.0",
    "CLIENT_ID": "your-client-id",
    "CLIENT_SECRET": "your-client-secret",
    "ORGANIZATION_ID": "ABC123@AdobeOrg",
    "SCOPES": "openid, AdobeID, additional_info.projectedProductContext",
    "AW_USERNAME": "user:acme",
    "AW_SECRET": "wsse-secret"
}
```

See the [Configuration reference in README.md](../README.md#configuration) for a description of every field.

> **API credentials:**
> - **API 2.0 (OAuth2):** `CLIENT_ID`, `CLIENT_SECRET`, `ORGANIZATION_ID` — create a Server-to-Server credential in the [Adobe I/O Console](https://console.adobe.io/) and add the **Adobe Analytics** product profile.
> - **API 1.4 (WSSE):** `AW_USERNAME`, `AW_SECRET` — found in Adobe Analytics under Admin → User Management → Users → Edit user → Web Services.

### 3d. Set the environment variable

```bash
export MERIDIAN_SECRETS_DIR=~/secrets/meridian
```

Add this to your shell profile (`~/.zshrc`, `~/.bashrc`, etc.) so it persists across sessions:

```bash
echo 'export MERIDIAN_SECRETS_DIR=~/secrets/meridian' >> ~/.zshrc
source ~/.zshrc
```

---

## 4. Verify Setup

```bash
uv run verify_setup.py
```

This checks that `MERIDIAN_SECRETS_DIR` is set, at least one client config is valid, required directories exist, and all imports succeed. Fix any errors it reports before proceeding.

---

## 5. Run the Application

```bash
uv run run.py
```

Expected output:

```
 * Running on http://127.0.0.1:5010
 * Debug mode: off
```

Open your browser to:

- **Brochure site:** `http://127.0.0.1:5010/`
- **Client dashboard:** `http://127.0.0.1:5010/acme/` (replace `acme` with your client slug)

The background cache warmer will start pre-fetching data from the Adobe Analytics API. The first load of any page may be slower while the cache warms up.

### Custom port

```bash
PORT=5011 uv run run.py
```

---

## 6. Adding a Second Client

Drop another JSON file in the same secrets directory:

```bash
cp ~/secrets/meridian/acme.json ~/secrets/meridian/betacorp.json
# edit betacorp.json with different credentials
```

Restart the app. The new client is available at `http://127.0.0.1:5010/betacorp/` with no code changes.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `RuntimeError: MERIDIAN_SECRETS_DIR is not set` | Env var missing | Run `export MERIDIAN_SECRETS_DIR=<path>` |
| `No valid client configs found` | Secrets dir is empty or files have invalid JSON | Check file syntax with `python -m json.tool <file>` |
| `401 Unauthorized` from API | Wrong credentials | Verify `CLIENT_ID`, `CLIENT_SECRET`, and `ORGANIZATION_ID` in your config |
| API 1.4 pages show an error banner | Adobe 1.4 API unreachable | Adobe's 1.4 infrastructure is being deprecated; Meridian retries on `api2`–`api4.omniture.com` automatically |
| Port already in use | Another process on 5010 | Use `PORT=5011 uv run run.py` |

---

*Last updated: 2026-04-15*
