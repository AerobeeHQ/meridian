"""
Codex - Adobe Analytics Configuration Viewer
Flask application factory
"""
import json
import os
from flask import Flask

from app.services.git_info import get_git_info


def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"config.json not found at {config_path}. "
            "Copy config.dist.json to config.json and fill in your credentials."
        )

    with open(config_path, 'r') as f:
        return json.load(f)


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Load configuration
    config = load_config()
    app.config['APP_TITLE'] = config.get('APP_TITLE', 'Codex')
    app.config['AW_REPORTSUITE_ID'] = config.get('AW_REPORTSUITE_ID')
    app.config['REPORTSUITE_NAME'] = config.get('REPORTSUITE_NAME', '')

    # API version selection (default: 2.0)
    app.config['API_VERSION'] = config.get('API_VERSION', '2.0')

    # OAuth2 credentials (API 2.0)
    app.config['CLIENT_ID'] = config.get('CLIENT_ID')
    app.config['CLIENT_SECRET'] = config.get('CLIENT_SECRET')
    app.config['SCOPES'] = config.get('SCOPES')
    app.config['ORGANIZATION_ID'] = config.get('ORGANIZATION_ID')

    # WSSE credentials (API 1.4 - also used for processing rules)
    app.config['AW_USERNAME'] = config.get('AW_USERNAME')
    app.config['AW_SECRET'] = config.get('AW_SECRET')

    # API 1.4 request timeout (seconds); see config.dist.json for guidance
    app.config['API_V14_TIMEOUT'] = config.get('API_V14_TIMEOUT', 5.0)

    # Adobe Launch (Tags) integration - Roadmap v2-003
    app.config['LAUNCH_ENABLED'] = config.get('LAUNCH_ENABLED', False)
    app.config['LAUNCH_PROPERTY_ID'] = config.get('LAUNCH_PROPERTY_ID')
    app.config['LAUNCHPAD_URL'] = config.get('LAUNCHPAD_URL', '')
    app.config['LAUNCH_SCOPES'] = config.get('LAUNCH_SCOPES')  # None = use default

    # Auth mode - Roadmap v2-004
    # 'server' = service account OAuth2 (default, current behaviour)
    # 'user'   = per-user Adobe IMS login via Authorization Code flow
    app.config['AUTH_MODE'] = config.get('AUTH_MODE', 'server')
    app.config['OAUTH_REDIRECT_URI'] = config.get('OAUTH_REDIRECT_URI')
    if config.get('SESSION_SECRET'):
        app.secret_key = config['SESSION_SECRET']

    # Git info for footer display
    git_info = get_git_info()
    app.config['GIT_BRANCH'] = git_info.get('branch')
    app.config['GIT_COMMIT'] = git_info.get('commit')

    # ── Service instantiation ─────────────────────────────────────────────────
    # Services are created once here and stored on the app object so every part
    # of the codebase (routes, cache warmer) shares the same instances without
    # each having to re-implement the init logic.

    from app.services.adobe_auth import OAuth2Auth
    from app.services.adobe_analytics_v2 import AdobeAnalyticsV2Service
    from app.services.adobe_analytics import AdobeAnalyticsService

    if app.config['API_VERSION'] == '2.0':
        auth = OAuth2Auth(
            client_id=app.config['CLIENT_ID'],
            client_secret=app.config['CLIENT_SECRET'],
            scopes=app.config.get('SCOPES'),
        )
        app.codex_api_service_v2 = AdobeAnalyticsV2Service(
            auth_service=auth,
            client_id=app.config['CLIENT_ID'],
            org_id=app.config['ORGANIZATION_ID'],
        )

    app.codex_api_service_v14 = AdobeAnalyticsService(
        username=app.config['AW_USERNAME'],
        secret=app.config['AW_SECRET'],
        request_timeout=app.config.get('API_V14_TIMEOUT', 5.0),
    )

    # Adobe Launch (Tags) service — only when LAUNCH_ENABLED and API 2.0
    if app.config['LAUNCH_ENABLED'] and app.config.get('LAUNCH_PROPERTY_ID'):
        if app.config['API_VERSION'] == '2.0':
            from app.services.adobe_launch import AdobeLaunchService
            # The Reactor API requires broader IMS scopes than Analytics alone.
            # Specifically, read_organizations and additional_info.roles are needed.
            # These match the scopes launchpy uses for successful Reactor API access.
            # A dedicated OAuth2Auth instance is created so the narrower Analytics
            # token is not affected.
            _launch_scopes = app.config.get('LAUNCH_SCOPES') or (
                'AdobeID, openid, read_organizations, '
                'additional_info.job_function, '
                'additional_info.projectedProductContext, additional_info.roles'
            )
            _launch_auth = OAuth2Auth(
                client_id=app.config['CLIENT_ID'],
                client_secret=app.config['CLIENT_SECRET'],
                scopes=_launch_scopes,
            )
            app.codex_launch_service = AdobeLaunchService(
                auth_service=_launch_auth,
                org_id=app.config['ORGANIZATION_ID'],
            )

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # ── Background cache warmer ───────────────────────────────────────────────
    from app.services.cache_warmer import start_scheduler
    app.cache_scheduler = start_scheduler(app)

    return app
