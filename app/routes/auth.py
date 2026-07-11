"""
Auth routes for Meridian — Roadmap v2-004 (User OAuth Login)

This blueprint is a stub that establishes the routing structure for per-user
Adobe IMS OAuth login.  All routes currently return placeholder responses;
implementation happens in v2-004.

When AUTH_MODE is 'server' (the default), this blueprint exists but is never
reached — the before_request guard (added in v2-004) only activates for
'user' mode.

Route summary:
    GET /auth/login    — Redirect the browser to Adobe IMS authorisation URL
    GET /auth/callback — Handle the IMS redirect; exchange code for token
    GET /auth/logout   — Clear the user session and redirect to /auth/login
"""
from flask import Blueprint, redirect, url_for

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login')
def login():
    """Initiate Adobe IMS OAuth Authorization Code flow.

    Constructs the IMS authorisation URL and redirects the user's browser
    to Adobe login.  Not yet implemented — placeholder for v2-004.
    """
    # v2-004: build IMS authorize URL with CLIENT_ID, OAUTH_REDIRECT_URI,
    # required scopes, and response_type=code, then return redirect(ims_url).
    return 'Adobe IMS login not yet implemented (v2-004).', 501


@auth_bp.route('/callback')
def callback():
    """Handle the Adobe IMS redirect after successful user login.

    Exchanges the authorisation code for an access token + refresh token and
    stores them in the Flask session.  Not yet implemented — placeholder for v2-004.
    """
    # v2-004: extract 'code' from request.args, POST to IMS token endpoint,
    # store access_token + refresh_token in session, redirect to '/'.
    return 'OAuth callback not yet implemented (v2-004).', 501


@auth_bp.route('/logout')
def logout():
    """Clear the user session and redirect to the login page.

    Not yet implemented — placeholder for v2-004.
    """
    # v2-004: session.clear(), then redirect to url_for('auth.login').
    return redirect(url_for('auth.login'))
