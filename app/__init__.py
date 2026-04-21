"""
Codex - Adobe Analytics Configuration Viewer
Flask application factory
"""
import os
from flask import Flask

from app.services.git_info import get_git_info
from app.services.config_loader import load_clients


def _build_client_services(client_slug: str, config: dict) -> dict:
    """Instantiate API services for one client config and return them in a dict."""
    from app.services.adobe_auth import OAuth2Auth
    from app.services.adobe_analytics_v2 import AdobeAnalyticsV2Service
    from app.services.adobe_analytics import AdobeAnalyticsService
    from app.services.cache import CacheService

    api_version = config.get('API_VERSION', '2.0')

    api_v2 = None
    if api_version == '2.0':
        _required_v2_keys = ('CLIENT_ID', 'CLIENT_SECRET', 'ORGANIZATION_ID')
        _missing = [k for k in _required_v2_keys if not config.get(k)]
        if _missing:
            raise RuntimeError(
                f"Client '{client_slug}' is configured for API 2.0 but is missing "
                f"required key(s): {', '.join(_missing)}"
            )
        auth = OAuth2Auth(
            client_id=config['CLIENT_ID'],
            client_secret=config['CLIENT_SECRET'],
            scopes=config.get('SCOPES'),
        )
        api_v2 = AdobeAnalyticsV2Service(
            auth_service=auth,
            client_id=config['CLIENT_ID'],
            org_id=config['ORGANIZATION_ID'],
        )

    api_v14 = AdobeAnalyticsService(
        username=config.get('AW_USERNAME'),
        secret=config.get('AW_SECRET'),
        request_timeout=config.get('API_V14_TIMEOUT', 5.0),
    )

    launch = None
    if config.get('LAUNCH_ENABLED') and config.get('LAUNCH_PROPERTY_ID') and api_version == '2.0':
        from app.services.adobe_launch import AdobeLaunchService
        _launch_scopes = config.get('LAUNCH_SCOPES') or (
            'AdobeID, openid, read_organizations, '
            'additional_info.job_function, '
            'additional_info.projectedProductContext, additional_info.roles'
        )
        _launch_auth = OAuth2Auth(
            client_id=config['CLIENT_ID'],
            client_secret=config['CLIENT_SECRET'],
            scopes=_launch_scopes,
        )
        launch = AdobeLaunchService(
            auth_service=_launch_auth,
            org_id=config['ORGANIZATION_ID'],
        )

    # Per-client cache directory.
    # Prefer $CODEX_SECRETS_DIR/cache/<slug> so cached data persists on the
    # mounted secrets volume in Docker.  Fall back to {project_root}/cache/<slug>
    # for local development where the env var may not be set.
    _secrets_dir = os.environ.get('CODEX_SECRETS_DIR')
    if _secrets_dir:
        cache_dir = os.path.join(_secrets_dir, 'cache', client_slug)
    else:
        cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'cache', client_slug,
        )
    os.makedirs(cache_dir, exist_ok=True)
    cache = CacheService(cache_dir=cache_dir)

    return {
        'config':  config,
        'api_v2':  api_v2,
        'api_v14': api_v14,
        'launch':  launch,
        'cache':   cache,
    }


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # ── Load all client configurations ────────────────────────────────────────
    clients_config = load_clients()

    # ── Build per-client service bundles ──────────────────────────────────────
    app.codex_clients = {
        slug: _build_client_services(slug, cfg)
        for slug, cfg in clients_config.items()
    }

    # ── App-level settings ────────────────────────────────────────────────────
    # SESSION_SECRET and AUTH_MODE are taken from the first loaded client config
    # (alphabetical order). Override by setting CODEX_SESSION_SECRET env var.
    first_config = next(iter(clients_config.values()))

    session_secret = os.environ.get('CODEX_SESSION_SECRET') or first_config.get('SESSION_SECRET')
    if session_secret:
        app.secret_key = session_secret

    # Git info for footer display
    git_info = get_git_info()
    app.config['GIT_BRANCH'] = git_info.get('branch')
    app.config['GIT_COMMIT'] = git_info.get('commit')

    # Expose the list of valid client slugs for routing validation
    app.config['CODEX_CLIENT_SLUGS'] = set(app.codex_clients.keys())

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # ── Root route ────────────────────────────────────────────────────────────
    # Serve the brochure site at the root. Client apps live at /<client>/.
    @app.route('/')
    def root():
        from flask import render_template
        return render_template('brochure.html')

    # ── Background cache warmer ───────────────────────────────────────────────
    from app.services.cache_warmer import start_scheduler
    app.cache_scheduler = start_scheduler(app)

    return app
