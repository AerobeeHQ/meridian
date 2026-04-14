# 052 — Multisite Routing with Per-Client URL Prefix and Secrets Directory

**Date:** 2026-04-14
**PR:** [#67](https://github.com/maxisdigital/codex/pull/67)
**Branch:** `feature/multisite-routing` (merged to `main`)
**Status:** Complete

---

## Problem

Codex was hard-wired for a single client: one `config.json`, one report suite, one URL root. To serve multiple clients (e.g. Maxis, Coles) from the same deployment:

- All routes lived at `/evars`, `/props`, etc. — no client namespace.
- The config file was committed to the repo (git-ignored but easily leaked) or passed as a mounted Docker volume, making multi-client setups awkward.
- Cache was flat: `cache/<rsid>.json` — no isolation between clients.

---

## Solution

### Per-client URL prefix

All routes are now prefixed with `/<client>/` (e.g. `/maxis/evars`, `/coles/props`). The root `/` redirects to the first configured client for convenience.

Client context is injected **without changing route function signatures** using Flask's `url_value_preprocessor` and `url_defaults` hooks:
- `url_value_preprocessor` pops `client` from URL kwargs and stores it on `flask.g`.
- `url_defaults` reinserts `client` when building URLs with `url_for()`, so templates are unchanged.
- A `before_request` hook validates that the client slug is known, returning a 404 for unknown prefixes.

### Secrets directory (`CODEX_SECRETS_DIR`)

Credentials are no longer mounted as a single `config.json`. Instead, `CODEX_SECRETS_DIR` points to a directory of per-client JSON files:

```
$CODEX_SECRETS_DIR/
├── maxis.json
└── coles.json
```

`app/services/config_loader.py` scans this directory at startup, validates required keys (`AW_REPORTSUITE_ID`, `API_VERSION`), and returns a slug-keyed dict. Files prefixed with `_` are reserved for future app-level settings and are skipped.

The app fails loudly at startup if `CODEX_SECRETS_DIR` is unset or contains no valid configs.

### Per-client service isolation

`app/__init__.py` builds `app.codex_clients` — a dict of `{slug: {config, api_v2, api_v14, launch, cache}}`. Each client gets its own:
- OAuth2 auth service and Analytics 2.0 client
- API 1.4 (WSSE) client
- Adobe Launch service (if `LAUNCH_ENABLED`)
- Cache directory: `cache/<client_slug>/<rsid>.json`

`SESSION_SECRET` is taken from the first client config alphabetically, or overridden via `CODEX_SESSION_SECRET` env var.

### Cache warmer

`cache_warmer.py` iterates all clients and warms each at startup and every 24h. Log output is prefixed with `[<client>]` for easy filtering.

---

## Challenges

### 1. Route decorator mass-rename

~50 route decorators (`@main_bp.route('/evars')`) needed the `/<client>/` prefix added. Done via `sed` in a single pass. No route function signatures were changed — all client context flows through `flask.g`.

### 2. `inject_globals` crashing outside client context

The Jinja2 context processor (`inject_globals`) was calling `g.api` and `g.client_config` unconditionally. This crashed on the root `/` route (which has no client in context) and on static file requests.

Fixed by using `g.get('api')` and `client_config.get(key, default)` instead of direct attribute access. A Copilot PR fix (commit `1ab93804`) introduced the guard; a follow-up (commit `241d0555`) tightened API 2.0 key validation.

### 3. API 2.0 key validation timing

Initial implementation validated API 2.0 keys lazily (at first request). This meant a misconfigured client would fail silently until a route was hit. Moved validation into `_build_client_services()` at startup so bad configs are caught immediately with a clear `RuntimeError`.

### 4. docker-compose.yml not updated

The original `docker-compose.yml` still mounted `./config.json` and set no `CODEX_SECRETS_DIR`. Updated separately (see docker-compose.yml changes) to mount a `./secrets` directory and pass the env var.

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/config_loader.py` | New — scans `CODEX_SECRETS_DIR`, validates and returns client configs |
| `app/__init__.py` | Replaced single-client wiring with `app.codex_clients` dict; per-client service builder |
| `app/routes/main.py` | Client routing hooks (`url_value_preprocessor`, `url_defaults`, `before_request`); all routes prefixed `/<client>/`; helpers read from `g` |
| `app/services/cache_warmer.py` | Iterates all clients; per-client log prefix |
| `config.dist.json` | Added `_WARNING` comment about credentials |
| `site/templates/index.html` | Demo links updated to `/maxis/` |
| `docker-compose.yml` | Removed `config.json` mount; added `secrets` volume and `CODEX_SECRETS_DIR` |
| `docs/autopsies/052-multisite-routing.md` | New — this document |

---

## Migration from single-client setup

```bash
mkdir -p /path/to/secrets/codex
cp config.json /path/to/secrets/codex/maxis.json
export CODEX_SECRETS_DIR=/path/to/secrets/codex
uv run run.py
```

For Docker, create a `secrets/` directory next to `docker-compose.yml`:

```bash
mkdir -p secrets
cp config.json secrets/maxis.json
docker compose up -d --build
```

---

## Notes

- The `/<client>/` prefix is enforced in routing, not in a reverse proxy — no Nginx config changes needed.
- Adding a second client is as simple as dropping another JSON file in `$CODEX_SECRETS_DIR` and restarting.
- The cache warmer runs for all clients on the same schedule; if clients have very different cache TTLs, consider making the interval configurable per-client in a future pass.
- `SESSION_SECRET` is shared across all clients (taken from first config). This is intentional for now — sessions are not client-scoped, so a single secret is correct.
