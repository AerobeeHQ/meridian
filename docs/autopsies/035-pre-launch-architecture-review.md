# 035 — Pre-Launch Architecture Review

**Date:** 2026-03-27
**Status:** Complete — merged in PR #46 (`refactor/pre-launch-cleanup`)
**Scope:** Full codebase review in preparation for v2-003 (Adobe Launch Integration) and v2-004 (User OAuth Login)

---

## Purpose

Before implementing the two largest items on the v2 roadmap, a structured review was conducted to:

1. Assess whether the current architecture can support both features without major rework.
2. Identify quick wins and simple cleanup items worth doing first.
3. Surface anything that would actively block or complicate the upcoming work.

Three parallel review agents covered:
- **Agent A** — Service layer, OAuth, cache, app factory
- **Agent B** — Routes, templates, navigation
- **Agent C** — Config, project structure, Dockerfile, todo list

---

## Summary Verdict

**The architecture is sound and ready to extend.** There are no blockers. v2-003 and v2-004 can be started on the current codebase. However, there are several low-to-medium effort improvements that would make both features easier to implement and maintain. These are catalogued below.

---

## Findings by Area

### 1. Auth (`app/services/adobe_auth.py`)

The `OAuth2Auth` class is clean and well-structured. Token caching is in-memory with a 5-minute expiry buffer. Token injection works correctly via `_get_headers()` in the v2 service.

**Limitations relevant to v2-004:**
- Token is stored on the app object — a single shared instance. There is no concept of a per-user token.
- No session layer exists anywhere in the codebase. Adding user OAuth will require Flask session setup, a `UserOAuth` class alongside `OAuth2Auth`, and a `before_request` login guard.

**Relevant to v2-003:**
- The Reactor API uses the same OAuth2 IMS endpoint and likely the same `CLIENT_ID`/`CLIENT_SECRET`, but with different scopes. `AdobeLaunchService` can re-use `OAuth2Auth` directly — just pass it different scopes at instantiation. No refactoring needed.

### 2. Service Layer (`app/services/`)

Services are well-separated and appropriately scoped. The pattern is consistent: `OAuth2Auth` → `AdobeAnalyticsV2Service` → `CacheService` → route.

**Duplication issue:** Service instantiation happens in two places independently:
- `app/routes/main.py` lines ~117–128 (lazy init on app object)
- `app/services/cache_warmer.py` lines ~29–45

Both create `OAuth2Auth` and service instances from config. This works but means changes to instantiation logic must be made in two places. Worth centralising before the codebase grows further.

**Cache service:** Solid, file-based JSON with per-key TTL. Known minor weaknesses: no file locking (race condition possible under concurrent writes), no automatic cleanup of expired keys. Neither is a blocker for v2-003/004.

**`AdobeAnalyticsV2Service` internal caching:** Discovery data and global company ID are cached on the service instance for the process lifetime. No refresh mechanism. Not a practical issue given how rarely these change.

### 3. Routes (`app/routes/main.py`)

`main.py` is **2,103 lines** — it has grown significantly and will become a maintenance burden as v2-003 and v2-004 add new routes. Current domains handled in a single file:

- Core dimensions (props, eVars, events, ListVars)
- Processing rules, marketing channels
- Segments, calculated metrics
- Report suites, cache management, overview
- API fragments (`/api/components`, `/api/related-rules`, `/api/notes/*`)
- Debug proxy (`/debug`, `/debug/call`)

Splitting into blueprints is the right long-term direction but carries re-registration risk. The clearest, lowest-risk split would be extracting the debug routes first (self-contained), then auth routes (new for v2-004 anyway). The rest can wait.

**Helper functions that have grown in main.py:**
- `find_related_processing_rules()`, `format_rule_html()`, `_expand_bracket_list()` — rule formatting logic
- `_parse_segment_schema()`, `_walk_formula()` — segment/metric parsing
- `_parse_calc_metric_formula()` — formula tree walker
- `generate_csv()`, `transform_data()` — export logic
- `_load_debug_endpoints()` — Swagger parsing

These work fine but are contributing to file size. Extraction to service modules would help if/when the file is split.

**Security note:** `_render_api_error()` includes Python tracebacks in the rendered error page. In the current single-developer deployment this is acceptable, but it should be gated behind debug mode before any wider deployment.

### 4. Templates

Templates use Jinja2 macros (`_macros.html`) effectively for repeated patterns (trend charts, notes form, components accordion, related rules). This is good practice.

**Significant duplication in detail page templates:**
- `detail.html` (322 lines), `event_detail.html` (238 lines), `listvar_detail.html` (249 lines) are approximately 75% structurally identical.
- All three have: two-column header, config table, notes form, stats cards, async placeholders, chart, async JS loaders.
- The variation is only in the config table rows and chart labels.

Consolidating these into a single base detail template with Jinja2 `block` overrides would reduce template code by ~400 lines and make future changes (e.g., adding a "Related Launch Rules" section for v2-003) a one-place change rather than three.

**Navigation (`base.html`):**
- The navbar has no right-side user menu area — all links are left-aligned.
- v2-004 requires a login/logout/user display in the navbar.
- Bootstrap's `ms-auto` pattern is available to push a right-side `<ul>` into position with minimal change to the existing markup.

**Inline CSS:**
- `base.html` contains ~159 lines of CSS in a `<style>` block.
- Extracting this to `app/static/css/style.css` would be clean but is not a prerequisite for v2-003 or v2-004.

### 5. Config (`config.dist.json`)

The config template is clean and well-documented with `_comment_` entries. No outdated fields.

**Missing fields for upcoming features:**

| Key | For | Notes |
|-----|-----|-------|
| `LAUNCH_PROPERTY_ID` | v2-003 | The Tags property ID (PR...). Feature should be disabled if absent. |
| `LAUNCH_ENABLED` | v2-003 | Explicit feature flag; graceful degradation if false. |
| `AUTH_MODE` | v2-004 | `"server"` (default, current) or `"user"` (new). |
| `OAUTH_REDIRECT_URI` | v2-004 | Callback URL for user login flow. |
| `SESSION_SECRET` | v2-004 | Flask session signing key. Required if `AUTH_MODE = "user"`. |

### 6. Project Structure

**Swagger files:** `docs/adobe_analytics_api_1.4_swagger.json` and `docs/adobe_analytics_api_2.0_swagger.json` are referenced by the API debug page. They live in `docs/` for historical reasons but logically belong in `assets/`. The todo list (item 24) already flags this. Moving them requires updating `_DOCS_DIR` in `main.py` and the Dockerfile `COPY` directive.

**`notes/` directory:** Contains ~18 JSON files — user-generated dimension annotations. This is runtime data (correctly git-ignored) and is fine where it is. No action needed.

**`verify_setup.py`:** Comprehensive. Will need additions for v2-003 (warn if `LAUNCH_ENABLED=true` but `LAUNCH_PROPERTY_ID` missing) and v2-004 (require `SESSION_SECRET` and `OAUTH_REDIRECT_URI` if `AUTH_MODE=user`).

**`pyproject.toml`:** No new dependencies are needed for v2-003. For v2-004, Flask's built-in signed-cookie session is sufficient for single-instance deployment — no new package required at this stage. `flask-session` would only be needed for multi-instance Redis-backed sessions.

---

## Recommended Changes

Grouped by scope and risk. The user should approve before any changes are made.

### Group A — Simple, no-risk (≤1h each)

These are self-contained and have no impact on existing functionality.

| # | Change | Why |
|---|--------|-----|
| A1 | Add `LAUNCH_PROPERTY_ID`, `LAUNCH_ENABLED`, `AUTH_MODE`, `OAUTH_REDIRECT_URI`, `SESSION_SECRET` to `config.dist.json` with `_comment_` entries | Prepares config template for both upcoming features |
| A2 | Move Swagger files from `docs/` to `assets/swagger/`; update `_DOCS_DIR` in `main.py` and `COPY` in `Dockerfile` | Cleaner structure; addresses todo item 24 |
| A3 | Gate traceback display in `_render_api_error()` behind `app.debug` | Security hygiene before any wider deployment |
| A4 | Mark todo item 25 (this review) as complete; tick off API debug page (item 11) which is already shipped | Keeps todo.md accurate |

### Group B — Architectural preparation (medium, low risk)

These establish patterns needed directly by v2-003 and v2-004.

| # | Change | Why |
|---|--------|-----|
| B1 | Create `app/routes/auth.py` as an empty Blueprint with stub routes (`/auth/login`, `/auth/callback`, `/auth/logout`) | Establishes file structure for v2-004; keeps auth separate from main.py from day one |
| B2 | Add right-side user menu placeholder to `base.html` navbar (conditional on `AUTH_MODE`, hidden by default) | Avoids having to restructure the navbar mid-feature; the HTML change is trivial now |
| B3 | Centralise service instantiation: move OAuth2Auth + service init from both `main.py` and `cache_warmer.py` into `app/__init__.py` (or a new `app/services/factory.py`) | Eliminates duplication; makes adding `AdobeLaunchService` in v2-003 a one-place change |

### Group C — Deferred (worthwhile, but not before v2-003/004)

| # | Change | Why defer |
|---|--------|-----------|
| C1 | Consolidate `detail.html`, `event_detail.html`, `listvar_detail.html` into shared base template | High value but medium effort; risk of breaking detail pages. Better done after v2-003 adds a new section to all three. |
| C2 | Split `main.py` into multiple blueprints | High effort, non-trivial re-registration. Do after v2-004 adds `auth.py` and the pattern is established. |
| C3 | Extract inline CSS from `base.html` to `static/css/style.css` | No functional impact; purely cosmetic. Defer to a quiet period. |
| C4 | Trend charts for Props/eVars/ListVars (todo quick wins 1 and 5) | Tempting but out of scope for this review; separate PR. |

---

## Architecture Assessment for v2-003 and v2-004

### v2-003 (Adobe Launch / Reactor API)

**Readiness: High.** The service pattern is well-established. `AdobeLaunchService` will follow the exact same structure as `AdobeAnalyticsV2Service`:

- Inject `OAuth2Auth` (same credentials, additional scope)
- Different base URL (`https://reactor.adobe.io`)
- Cache via existing `CacheService` with a `launch_rules` key

The detail page pattern (Related Processing Rules section) already exists as a macro. Adding "Related Launch Rules" will be a copy-paste extension. The main unknown is the Reactor API's data shape — a Jupyter notebook spike is required before implementation (per the plan doc).

**Prerequisite:** Group B3 (centralised service init) would make adding `AdobeLaunchService` cleaner, but is not strictly required.

### v2-004 (User OAuth Login)

**Readiness: Medium.** The auth service layer is well-written but architecturally single-tenant. The gaps are:

1. No session layer — Flask's built-in is sufficient; just needs `app.secret_key = config['SESSION_SECRET']` in `__init__.py`
2. No user routes — `app/routes/auth.py` needs to be created (Group B1)
3. No navbar user area — base.html needs the right-side menu (Group B2)
4. `AdobeAnalyticsV2Service` receives its token at instantiation, not per-request — this will need to accept a per-user token. The simplest approach is a parameter to `_make_request()` or a lightweight factory function.

**Recommended order:** Do Group A and B1/B2 first, then implement v2-003 (lower architectural risk), then v2-004.

---

## Files Reviewed

| File | Lines | Notes |
|------|-------|-------|
| `app/routes/main.py` | 2,103 | Primary concern: size |
| `app/services/adobe_auth.py` | ~120 | Clean; single-tenant assumption |
| `app/services/adobe_analytics_v2.py` | ~350 | Solid; internal caching is fine |
| `app/services/adobe_analytics.py` | ~430 | Solid; endpoint rotation is well-handled |
| `app/services/cache.py` | ~260 | File-based, per-key TTL; no blockers |
| `app/services/cache_warmer.py` | ~80 | Duplicates service init logic |
| `app/services/notes.py` | ~90 | Clean; good path traversal protection |
| `app/__init__.py` | ~70 | Good factory pattern |
| `app/templates/base.html` | ~337 | Navbar needs user menu area |
| `app/templates/detail.html` | 322 | 75% overlap with event/listvar detail |
| `app/templates/event_detail.html` | 238 | See above |
| `app/templates/listvar_detail.html` | 249 | See above |
| `app/templates/_macros.html` | ~754 | Well-structured; `notes_form_js` is large |
| `config.dist.json` | — | Missing v2-003/004 fields |
| `verify_setup.py` | — | Needs additions for new features |
| `Dockerfile` | — | Already copies `docs/`; swagger move needed |
| `pyproject.toml` | — | No new deps needed at this stage |

## Implementation

All Group A and Group B items were implemented in a single PR on branch `refactor/pre-launch-cleanup` (PR #46). Group C remains deferred.

### Commits

| Commit | Description |
|--------|-------------|
| `03edf68` | Main refactor — all Group A and B changes |
| `137c7be` | Bug fix: restore `AdobeAnalyticsV2Service` import removed during B3 (still needed for `parse_description_metadata` static method in `evar_detail`) |
| `511c9c0` | Bug fix: coerce non-numeric API values (`"N/A"`) to `0` in `get_metric_trend()` and `get_event_trend()` — fixing `TypeError` on Calculated Metrics detail pages |

### What was done

**A1 — Config fields added (`config.dist.json`)**

Five new fields added with `_comment_` documentation:
- `LAUNCH_ENABLED` / `LAUNCH_PROPERTY_ID` — for v2-003 (Adobe Launch)
- `AUTH_MODE` / `OAUTH_REDIRECT_URI` / `SESSION_SECRET` — for v2-004 (User OAuth)

**A2 — Swagger files moved to `assets/swagger/`**

- `docs/adobe_analytics_api_1.4_swagger.json` → `assets/swagger/`
- `docs/adobe_analytics_api_2.0_swagger.json` → `assets/swagger/`
- `main.py`: `_DOCS_DIR` constant renamed to `_ASSETS_DIR`; swagger paths updated
- `Dockerfile`: `COPY docs/ docs/` replaced with `COPY assets/ assets/`

**A3 — Traceback gated behind `app.debug`**

`_render_api_error()` now passes `traceback_text=None` in production. Full traceback only included when `app.debug is True`.

**A4 — `todo.md` updated**

Completed items ticked off; swagger move item marked done.

**B1 — `app/routes/auth.py` created**

New Blueprint stub with three placeholder routes registered in `create_app()`:
- `GET /auth/login` — will redirect to Adobe IMS
- `GET /auth/callback` — will handle code exchange
- `GET /auth/logout` — will clear session

**B2 — Navbar user menu added (`base.html`)**

- Left nav given `me-auto` class
- Right-side `<ul class="navbar-nav ms-auto">` added, rendered only when `config.AUTH_MODE == 'user'`
- Shows login link when no session, user email + logout dropdown when session present

**B3 — Service instantiation centralised (`app/__init__.py`)**

`create_app()` now owns all service creation:
- `AdobeAnalyticsV2Service` (when `API_VERSION == '2.0'`)
- `AdobeAnalyticsService` (always, for processing rules)
- `app.secret_key` set from `SESSION_SECRET` if present

`get_api_service()` and `get_api_service_v14()` in `main.py` reduced to single-line attribute accessors. `cache_warmer.py` duplicate `_get_api_service_v2/_v14` helpers removed; fetch-map guards against `api_v2` being `None` in 1.4-only mode.

### What remains deferred (Group C)

| Item | When to revisit |
|------|----------------|
| Consolidate detail page templates | After v2-003 adds a "Related Launch Rules" section to all three — do it as part of that PR |
| Split `main.py` into blueprints | After v2-004 adds `auth.py` and the pattern is established |
| Extract inline CSS to `static/css/style.css` | Any quiet period; purely cosmetic |

---

## Brain farts

### Question

> Is Flask still the right microframework, or would I be better served migrating to something else like FastAPI, Django, Falcon, other? Once the Oauth Login and Launch integration is done, I would expect development to slow down; we would be reaching feature complete stage; and moving to
hosting the application for 2 or 3 clients, with maybe 5-10 visitors max at a time.

### Answer

Flask is the right call. Don't migrate.

Here's the reasoning:
Your usage profile is a perfect Flask fit:
- Server-side rendered Jinja2 templates (Flask's native pattern)
- 5–10 concurrent users maximum — Flask handles thousands; you'll never stress it
- 2–3 client deployments, not a SaaS platform
- No real-time requirements, no websockets, no heavy async workloads
- Already at or near feature-complete

Why the alternatives don't improve your situation:

- FastAPI — shines for async, high-throughput JSON APIs and auto-generated OpenAPI docs. You're not building an API product; you're building an internal tool with server-rendered HTML. FastAPI would require rewriting all your Jinja2 templates to a JS frontend or switching rendering model
entirely. Not worth it.
- Django — appropriate when you need ORM, admin panel, auth system, migrations. You're using flat JSON files for cache and notes, Adobe IMS for auth, and have no relational database. Django brings a lot of machinery for problems you don't have.
- Falcon — purely for API microservices, no templating. Wrong tool entirely.

The one legitimate consideration: v2-004 (User OAuth) introduces Flask sessions. Flask's built-in signed-cookie session is fine for 5–10 users on a single instance. You won't need Redis or flask-session unless you go multi-instance, which your client profile doesn't require.

Bottom line: The framework is not your bottleneck and never will be at this scale. The time you'd spend on a migration would be better spent on v2-003, v2-004, or improving observability for clients. Finish the roadmap, then stabilise.
