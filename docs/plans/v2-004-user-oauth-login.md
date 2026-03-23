# Plan: User OAuth Login

**Roadmap item:** Enable user OAuth login instead of Server-to-Server credentials.

**Complexity: High**

---

## Overview

Currently Codex uses Adobe's **Server-to-Server OAuth2** (client credentials grant) — a single set of API keys in `config.json` that authenticate as a service account. This works well for a single-user or internal deployment. Switching to **user-based OAuth** means individuals log in with their own Adobe IMS account, and the app makes API calls on their behalf.

This is a significant architectural change touching auth, sessions, API calls, and deployment configuration.

---

## Current Auth Architecture

- `adobe_auth.py` → `OAuth2Auth` class uses `client_credentials` grant.
- A single token is cached in memory on the Flask app object.
- All API calls share the same token.
- No user identity, no sessions, no login/logout.

---

## Target Architecture

- Users visit the app → redirected to Adobe IMS login page.
- After login, Adobe redirects back with an authorization code.
- App exchanges the code for a user-scoped access token + refresh token.
- API calls use the user's token (scoped to their Adobe org permissions).
- Sessions store per-user tokens (server-side session or signed cookie).

---

## Implementation Plan

### Step 1 — Adobe I/O Console configuration

Before writing any code:

1. In the Adobe I/O Console, add a **User authentication** credential (OAuth Web App) alongside the existing Server-to-Server credential.
2. Set the redirect URI (e.g. `http://localhost:5010/auth/callback` for dev, production URL for prod).
3. Note the new `CLIENT_ID` (may be the same) and confirm required scopes.

### Step 2 — New config fields

```json
{
  "AUTH_MODE": "user",
  "OAUTH_REDIRECT_URI": "http://localhost:5010/auth/callback",
  "SESSION_SECRET": "a-random-secret-key"
}
```

`AUTH_MODE` allows toggling between `"server"` (current default) and `"user"`.

### Step 3 — Flask session configuration

Add to `app/__init__.py` or `run.py`:

```python
app.secret_key = config['SESSION_SECRET']
```

Flask's built-in signed-cookie session is sufficient for a single-server deployment. For multi-instance, use `flask-session` with file or Redis backend.

### Step 4 — New auth routes

Add to `app/routes/main.py` (or a new `app/routes/auth.py`):

| Route | Purpose |
|-------|---------|
| `GET /auth/login` | Redirect to Adobe IMS authorization URL |
| `GET /auth/callback` | Handle redirect back; exchange code for token; store in session |
| `GET /auth/logout` | Clear session; redirect to login |

Adobe IMS authorization URL format:
```
https://ims-na1.adobelogin.com/ims/authorize/v2
  ?client_id={CLIENT_ID}
  &redirect_uri={REDIRECT_URI}
  &scope=openid,AdobeID,additional_info.projectedProductContext
  &response_type=code
```

Token exchange endpoint:
```
POST https://ims-na1.adobelogin.com/ims/token/v3
  client_id, client_secret, code, redirect_uri, grant_type=authorization_code
```

### Step 5 — Middleware: require login

Add a `before_request` handler that redirects to `/auth/login` if the session has no token, except for the `/auth/*` routes themselves.

```python
@app.before_request
def require_login():
    if config.get('AUTH_MODE') == 'user':
        if not session.get('access_token') and not request.path.startswith('/auth'):
            return redirect(url_for('auth.login'))
```

### Step 6 — Token refresh

User tokens expire (typically 24 hours). Store the `refresh_token` in the session and add logic to exchange it for a new access token before making API calls.

### Step 7 — Per-request token injection

Modify `AdobeAnalyticsV2Service` (or how it's instantiated per request) to accept a user token instead of always using the cached server-to-server token. The simplest approach: pass the token as a parameter to `_make_request()`.

---

## Files to Create / Change

| File | Change |
|------|--------|
| `app/routes/auth.py` | New: login, callback, logout routes |
| `app/routes/main.py` | Add `before_request` login guard; pass user token to service |
| `app/services/adobe_auth.py` | Add `UserOAuth` class alongside existing `OAuth2Auth` |
| `config.dist.json` | Add `AUTH_MODE`, `OAUTH_REDIRECT_URI`, `SESSION_SECRET` |
| `README.md` | Document user auth setup |

---

## Risks & Notes

- **Breaking change:** This replaces the current zero-login experience. All existing deployments would need reconfiguration.
- **Adobe I/O Console setup required:** The OAuth Web App credential must be configured before any code change.
- **Token storage:** Signed cookies work for single-user; multi-user deployments should consider a server-side session store.
- **Suggested approach:** Keep `AUTH_MODE: "server"` as the default so existing deployments continue working. User OAuth is opt-in.
- **Scope:** User tokens are scoped to the user's own Adobe org permissions — they'll only see report suites they have access to, which is a meaningful improvement for multi-team deployments.
