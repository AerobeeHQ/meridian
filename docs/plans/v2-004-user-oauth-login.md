# Plan: User OAuth Login

**Roadmap item:** v3-001 — User OAuth Login
**Complexity: High**
**Last revised: 2026-04-22**

---

## Overview

Currently Codex uses Adobe's **Server-to-Server OAuth2** (client credentials grant) — a single set of API keys in `config.json` that authenticate as a service account. This works well for a single-user or internal deployment.

The original plan was to replace this entirely with **user-based OAuth** (Authorization Code flow), so individuals log in with their own Adobe IMS account and the app makes API calls on their behalf.

**A critical constraint has been discovered:** Adobe's **Reactor (Tags/Launch) API does not support User OAuth authentication**. It requires Server-to-Server credentials. This means a full replacement of S2S is impossible while Reactor functionality exists.

This plan has been revised to reflect this constraint and proposes a **hybrid architecture**.

---

## Constraint: Reactor API Requires Server-to-Server

The Adobe Experience Platform Reactor API (`https://reactor.adobe.io`) only accepts tokens issued via the **client credentials** (S2S) grant. A user's personal IMS access token will be rejected with a 401 or 403.

Adobe Analytics API 2.0 (`https://analytics.adobe.io`) **does** support user OAuth tokens scoped with `AdobeID`, `openid`, and `additional_info.projectedProductContext`.

This split means:
- `AdobeAnalyticsV2Service` → **can use** a user token
- `AdobeLaunchService` → **must use** an S2S token

---

## Step 0 — Adobe Developer Console Setup (Before Writing Any Code)

This must be completed before any code is written. The OAuth credential must exist before testing the Authorization Code flow.

### 1. Add a User Authentication credential

In the [Adobe Developer Console](https://developer.adobe.com/console/):

1. Open your existing Project (the one that has the Server-to-Server credential for Codex).
2. Click **Add to Project → API**.
3. Select **Adobe Analytics** (and optionally **Experience Platform Launch** if it appears — but note Reactor does not use this credential).
4. Choose **User Authentication** → **OAuth Web App**.
5. The resulting `CLIENT_ID` may be the same as the S2S credential or a separate value — record whichever the console assigns.

### 2. Redirect URI constraints

The Developer Console enforces two redirect URI fields and they behave differently:

| Field | Requirement | Notes |
|-------|-------------|-------|
| **Default redirect URI** | Must start with `https://` | Used as the default if no `redirect_uri` param is passed in the auth request. |
| **Redirect URI pattern** | Regex (escaped) | Validates the `redirect_uri` query parameter in the auth request. Must match the redirect URI your app sends. |

**For production:** set both to your production HTTPS callback URL, e.g.:
- Default redirect URI: `https://codex.example.com/auth/callback`
- Redirect URI pattern: `https://codex\\.example\\.com/auth/callback`

### 3. Local development — the `http://localhost` problem

The console's `https://` requirement in the Default redirect URI field blocks plain `http://localhost` development setups. Options:

**Option A — Use ngrok (simplest)**
Run `ngrok http 5010` to get a temporary HTTPS tunnel. Set both redirect URI fields to the ngrok HTTPS URL. Re-register when the URL changes (free plan rotates URLs on restart). Consider `ngrok` with a fixed subdomain on a paid plan for stability.

**Option B — Flask with a self-signed TLS cert**
Run Flask in development with a self-signed cert:
```python
# run.py
app.run(ssl_context='adhoc')  # requires pyOpenSSL
```
Then register `https://localhost:5010/auth/callback`. The browser will show a cert warning (click through for dev). This keeps everything local.

**Option C — Separate dev credential with `https://localhost`**
Some Adobe console configurations accept `https://localhost` as an exception for development-only credentials. Worth testing — if the console accepts it, register a dedicated dev credential with `https://localhost:5010/auth/callback` and do not use it in production.

**Option D — Proxy via Caddy or mkcert**
Use `mkcert` to generate a locally-trusted cert for `localhost`, run Caddy as a reverse proxy on port 443, point to Flask on 5010. Most stable local HTTPS setup; one-time setup cost.

**Recommended for this project:** Option B (`ssl_context='adhoc'`) for a first pass; upgrade to Option D if the cert warning becomes annoying.

### 4. Redirect URI pattern syntax

The pattern field is a regex. Special characters (`.`) must be escaped with a double backslash in the console field. Examples:

| Intended match | Pattern to enter in console |
|---------------|-----------------------------|
| `https://codex.example.com/auth/callback` | `https://codex\\.example\\.com/auth/callback` |
| Any subdomain of example.com | `https://.*\\.example\\.com/auth/callback` |
| localhost (any port) | `https://localhost:\\d+/auth/callback` |

The `redirect_uri` parameter your app sends in the authorization request must match this pattern, otherwise Adobe IMS will reject the request before it reaches your callback.

### 5. Required scopes

Confirm the following scopes are enabled on the credential:

- `openid`
- `AdobeID`
- `additional_info.projectedProductContext` — needed to resolve report suite access

### 6. Record the new config values

After saving the credential, update `config.json` (in `CODEX_SECRETS_DIR`):

```json
{
  "AUTH_MODE": "user",
  "OAUTH_CLIENT_ID": "<from console — may differ from S2S CLIENT_ID>",
  "OAUTH_REDIRECT_URI": "https://localhost:5010/auth/callback",
  "SESSION_SECRET": "<generate with: python -c \"import secrets; print(secrets.token_hex(32))\">"
}
```

Keep `CLIENT_ID` / `CLIENT_SECRET` for the S2S credential unchanged — they are still needed for Reactor API calls.

---

## Architecture Options

### Option 1 — OAuth as Application Login Gate Only (Simpler)

Users authenticate with Adobe IMS purely to prove their identity. Once logged in, all API calls still use the shared S2S credential from config.

```
Browser → Adobe IMS login → confirms Adobe org membership
App → all API calls via S2S token (unchanged)
```

**Pros:**
- Simple to implement — no token-splitting logic
- App is behind a login wall without separate user management
- S2S code path unchanged; no risk of regressions
- Works identically for both Analytics and Reactor

**Cons:**
- Per-user report suite filtering is NOT achieved — all users see the same data
- The original goal of "users only see their own report suites" is not met
- Adds IMS login friction without meaningful data access improvement

**Best for:** Deployments that need an authentication wall (prevent anonymous access) but all authorised users should see the same data.

---

### Option 2 — OAuth Front Door + Hybrid API Calls (Recommended)

Users authenticate with their Adobe IMS account. The user's token is used for Analytics API calls. The S2S token (from config) is used for Reactor API calls. Both token types coexist.

```
Browser → Adobe IMS login → user access_token stored in session
Analytics API calls  → use user's access_token (per-user report suite scoping)
Reactor API calls    → use S2S token from config (shared service account)
```

**Pros:**
- Per-user report suite filtering IS achieved for Analytics
- Users only see the Analytics data they're personally permissioned for
- Reactor functionality continues without disruption
- S2S credential in config is no longer used for Analytics — reduced attack surface for the primary data path

**Cons:**
- Two token management paths to maintain
- S2S credentials remain required in config (can't deploy without them)
- Launch property visibility is not gated by the user's personal permissions (see Security section below)

**Best for:** Multi-user deployments where per-user Analytics data scoping is a meaningful requirement (different team members have different report suite access).

---

### Option 3 — Full OAuth (Future / Blocked by Adobe)

Replace S2S entirely. Requires Adobe to add user OAuth support to the Reactor API. Not currently possible.

---

## Recommended Approach: Option 2

Option 2 achieves the primary goal of user-scoped Analytics access while working within the Reactor API constraint. The S2S token for Reactor changes nothing about the current Reactor architecture — it already uses S2S.

The security concerns (see below) are real but manageable and should be documented.

---

## Security Analysis of Option 2

### Launch Property Visibility

**Issue:** A user who logs in via OAuth will see Launch/Reactor data (rules, data elements, extensions) fetched via the S2S service account. The S2S account may have access to Launch properties the user themselves would not have access to in the Adobe Experience Platform UI.

**Risk level:** Low to Medium, depending on deployment context.

**Mitigating factors:**
- In most internal deployments, all Analytics users have at least read access to the same Launch properties
- Launch property names and rules are generally not sensitive — they describe tagging implementation, not business data
- Codex only reads from Reactor; it does not write or modify any Launch configuration

**Mitigation options:**
1. **Document the limitation** — include a note in the UI (Settings page or footer) that Launch data is fetched via a shared service account and may not reflect the user's personal Launch permissions
2. **Property-level filtering** — if the Launch integration supports it, restrict visible properties to those associated with the user's accessible report suites (via the existing report suite → property mapping in Settings)
3. **Feature flag** — add `LAUNCH_ENABLED` config flag; orgs with strict permission requirements can disable Launch data entirely

### Token Storage in Flask Session

User `access_token` and `refresh_token` are stored in the signed Flask session cookie. This is acceptable for internal deployments with a strong `SESSION_SECRET`.

**For multi-instance deployments:** Use `flask-session` with a server-side store (Redis, filesystem) to avoid the cookie size limit and reduce token exposure in browser storage.

### CSRF Exposure

With a real login session, CSRF protection on write routes (`/api/notes`, `/api/tags`) becomes important. This is already tracked as v3-012 (HTTP Security Hardening) and should be resolved before or alongside v3-001.

### S2S Credential in Config

No change from the current risk profile. The S2S credential was already required and remains so. Ensure it is stored in `CODEX_SECRETS_DIR` (already enforced in the current architecture).

---

## Revised Target Architecture (Option 2)

### Auth Service Layer

Two token providers in `adobe_auth.py`:

```python
class OAuth2Auth:
    """Existing S2S client credentials — used for Reactor API calls."""
    # No changes needed

class UserAuth:
    """User OAuth Authorization Code flow — used for Analytics API calls."""

    AUTHORIZE_ENDPOINT = "https://ims-na1.adobelogin.com/ims/authorize/v2"
    TOKEN_ENDPOINT = "https://ims-na1.adobelogin.com/ims/token/v3"

    # Does NOT cache a token internally — user token lives in Flask session
    # Accepts the access_token from the session on each request

    def get_access_token(self, session: dict) -> str:
        """Return valid user token from session, refreshing if needed."""
        ...

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for access + refresh tokens."""
        ...

    def refresh(self, refresh_token: str) -> dict:
        """Refresh an expired access token."""
        ...
```

### Service Instantiation Per Request

`AdobeAnalyticsV2Service` receives the user token; `AdobeLaunchService` continues receiving the S2S `OAuth2Auth` instance.

```python
# In main.py / before_request or route context setup:

def get_analytics_service():
    user_token = session.get('access_token')
    if config['AUTH_MODE'] == 'user' and user_token:
        return AdobeAnalyticsV2Service(user_token=user_token, ...)
    else:
        return AdobeAnalyticsV2Service(auth=app.s2s_auth, ...)  # fallback

def get_launch_service():
    # Always uses S2S — Reactor API does not support user OAuth
    return AdobeLaunchService(auth=app.s2s_auth, ...)
```

### Auth Routes (`app/routes/auth.py`)

These are already stubbed. Full implementation:

| Route | Purpose |
|-------|---------|
| `GET /auth/login` | Redirect to Adobe IMS authorization URL |
| `GET /auth/callback` | Exchange code for tokens; store in session; redirect to `/` |
| `GET /auth/logout` | Clear session; redirect to `/auth/login` |

Adobe IMS authorization URL:
```
https://ims-na1.adobelogin.com/ims/authorize/v2
  ?client_id={CLIENT_ID}
  &redirect_uri={REDIRECT_URI}
  &scope=openid,AdobeID,additional_info.projectedProductContext
  &response_type=code
  &state={csrf_state_token}
```

### Login Guard

```python
@app.before_request
def require_login():
    if config.get('AUTH_MODE') == 'user':
        public_paths = ('/auth/', '/static/', '/health')
        if not session.get('access_token') and not request.path.startswith(public_paths):
            session['next'] = request.url  # remember intended destination
            return redirect(url_for('auth.login'))
```

### User Interface

The login experience is minimal:

1. **Login page** (`/auth/login`) — no HTML form needed; immediately redirects to Adobe IMS. A brief interstitial ("Redirecting to Adobe login…") is optional.
2. **Session banner** — add to `base.html` nav: display the logged-in user's name (from IMS profile) and a "Log out" link.
3. **Auth mode indicator** — Settings page shows current auth mode (`Server-to-Server` or `User OAuth`) with a note explaining that Launch data uses the shared service account.
4. **Token expiry handling** — if a refresh fails, clear the session and redirect to login with a flash message ("Your session has expired. Please log in again.").

### Obtaining the User Profile

After the token exchange, call IMS profile endpoint to get display name:

```
GET https://ims-na1.adobelogin.com/ims/profile
Authorization: Bearer {access_token}
```

Store `first_name`, `last_name`, `email` in session for display in the nav.

---

## Config

The existing S2S fields (`CLIENT_ID`, `CLIENT_SECRET`, `ORG_ID`) remain unchanged — they are still needed for Reactor. The new fields are additive:

```json
{
  "AUTH_MODE": "user",
  "OAUTH_CLIENT_ID": "<user-auth client ID from Developer Console — may equal CLIENT_ID>",
  "OAUTH_REDIRECT_URI": "https://localhost:5010/auth/callback",
  "SESSION_SECRET": "<python -c \"import secrets; print(secrets.token_hex(32))\">"
}
```

Note the `https://` scheme — required by the Adobe Developer Console (see Step 0).

`AUTH_MODE` values:
- `"server"` — current default; S2S for all APIs; no login required
- `"user"` — Adobe IMS login required; user token for Analytics, S2S for Reactor

`config.dist.json` already has `AUTH_MODE`, `OAUTH_REDIRECT_URI`, and `SESSION_SECRET` as stubs. Add `OAUTH_CLIENT_ID` to the dist file.

---

## Files to Create / Change

| File | Change |
|------|--------|
| `app/services/adobe_auth.py` | Add `UserAuth` class alongside existing `OAuth2Auth` |
| `app/routes/auth.py` | Implement login, callback, logout (stubs exist) |
| `app/routes/main.py` | Add `before_request` login guard; wire user token to Analytics service |
| `app/services/adobe_analytics_v2.py` | Accept `user_token` parameter as alternative to `OAuth2Auth` |
| `app/templates/base.html` | Add user name + logout link to nav when AUTH_MODE is user |
| `app/templates/settings.html` | Add auth mode info panel with Launch service account note |
| `config.dist.json` | `AUTH_MODE`, `OAUTH_REDIRECT_URI`, `SESSION_SECRET` already present |
| `README.md` | Document hybrid auth setup, required scopes, Reactor limitation |

---

## Dependency: v3-012 (HTTP Security Hardening)

CSRF protection on write routes should be in place before v3-001 ships, since real user sessions increase the CSRF risk surface. Consider implementing these together or sequencing v3-012 first.

---

## Risks & Notes

- **Reactor API limitation is permanent** (as of 2026-04-22): Adobe has confirmed user OAuth is not supported for the Reactor API. This constraint should be re-evaluated if Adobe updates their documentation.
- **Breaking change:** Switching `AUTH_MODE` to `user` changes the entire login experience. Existing single-user deployments may prefer to stay on `server` mode.
- **Adobe Developer Console setup required:** See Step 0. The OAuth Web App credential must be configured before coding begins. The redirect URI must use `https://` — use `ssl_context='adhoc'` in Flask for local dev (see options in Step 0). `OAUTH_CLIENT_ID` may equal the existing S2S `CLIENT_ID` or be a new value; confirm in the console.
- **Token storage:** Signed cookies (default Flask session) work for single-user. Multi-user deployments should use a server-side session store.
- **Report suite scoping:** User tokens restrict Analytics report suite access to what the user is personally permissioned for — this is the primary value delivered by this feature.
- **Launch property visibility is not per-user scoped** — this is a known limitation and should be communicated in the UI.
