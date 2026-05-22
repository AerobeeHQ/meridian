"""
Codex - Adobe Analytics Configuration Viewer
Flask application factory
"""
import os
import time
from flask import Flask

from app.services.git_info import get_git_info
from app.services.config_loader import load_clients


def _build_client_services(client_slug: str, config: dict) -> dict:
    """Instantiate API services for one client config and return them in a dict.

    Creates the following services based on the client's ``API_VERSION`` setting:

    - ``api_v2``:  ``AdobeAnalyticsV2Service`` (OAuth2, API 2.0) — only when
                   ``API_VERSION == '2.0'``.  Requires ``CLIENT_ID``,
                   ``CLIENT_SECRET``, and ``ORGANIZATION_ID`` in the config.
    - ``api_v14``: ``AdobeAnalyticsService`` (WSSE, API 1.4) — always created
                   because API 1.4 is still needed for processing rules, marketing
                   channels, and other endpoints not yet available in 2.0.
    - ``launch``:  ``AdobeLaunchService`` (Reactor API) — only when
                   ``API_VERSION == '2.0'``, ``LAUNCH_ENABLED`` is truthy,
                   and ``LAUNCH_PROPERTY_ID`` is provided.  Uses a separate
                   ``OAuth2Auth`` instance with the broader Reactor scopes.
    - ``cache``:   ``CacheService`` pointing to a per-client subdirectory so
                   different clients never share cached data.

    Args:
        client_slug: The client identifier (JSON filename stem, e.g. ``'maxis'``).
        config:      Client config dict loaded from the JSON secrets file.

    Returns:
        Dict with keys ``config``, ``api_v2``, ``api_v14``, ``launch``, ``cache``.

    Raises:
        RuntimeError: If ``API_VERSION == '2.0'`` but required OAuth keys are missing.
    """
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
    api_v14.discover_endpoint()

    launch = None
    if config.get('LAUNCH_ENABLED') and config.get('LAUNCH_PROPERTY_ID') and api_version == '2.0':
        from app.services.adobe_launch import AdobeLaunchService
        # The Reactor API requires broader scopes than the Analytics API, so
        # Launch gets its own OAuth2Auth instance with the full set of roles.
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
    # Prefer $CODEX_CACHE_DIR/<slug> (explicit writable cache mount in Docker).
    # Fall back to {project_root}/cache/<slug> for local development.
    # Each client gets its own subdirectory so their caches never overlap.
    _cache_root = os.environ.get('CODEX_CACHE_DIR') or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'cache'
    )
    cache_dir = os.path.join(_cache_root, client_slug)
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
    """Create and configure the Flask application.

    This is the Flask application factory.  It is called once at startup
    (by ``run.py`` or ``gunicorn``) and returns a fully configured ``Flask``
    instance.

    Multi-client architecture
    -------------------------
    Codex supports multiple Adobe Analytics clients from a single running
    instance.  Each client maps to one JSON file in ``CODEX_SECRETS_DIR``.
    At startup, every client gets its own bundle of services (API clients,
    cache) stored on ``app.codex_clients[slug]``.  Routes access the correct
    bundle via ``g`` (populated per-request by ``_load_client_context``).

    Returns:
        Configured ``Flask`` application instance.
    """
    app = Flask(__name__)
    app._start_time = time.monotonic()

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

    # ── Health check endpoint ─────────────────────────────────────────────────
    # Intentionally has no /<client>/ prefix so Docker / load balancers can hit
    # it without knowing a client slug.  Always returns HTTP 200 as long as the
    # process is alive and handling requests; callers should restart only on
    # network-level failure (connection refused / timeout), not on stale cache.
    @app.route('/health')
    def health():
        from flask import jsonify, current_app

        uptime_seconds = round(time.monotonic() - app._start_time)

        clients_info = []
        for slug, ctx in current_app.codex_clients.items():
            config = ctx['config']
            cache = ctx['cache']
            rsid = config.get('AW_REPORTSUITE_ID', '')

            # Use the dimensions cache key as a proxy for overall cache health.
            # This is a cheap file-stat operation — no outbound API calls.
            dim_key = {}
            cache_error = None
            if rsid:
                try:
                    cache_info = cache.get_info(rsid)
                    dim_key = cache_info.get('cache_keys', {}).get('dimensions', {})
                except Exception as exc:
                    cache_error = str(exc)

            cache_block = {
                'dimensions_fresh': None if cache_error else not dim_key.get('expired', True),
                'dimensions_age_mins': None if cache_error else dim_key.get('age_mins'),
            }
            if cache_error:
                cache_block['cache_info_error'] = cache_error

            clients_info.append({
                'slug': slug,
                'api_version': config.get('API_VERSION', '2.0'),
                'rsid': rsid,
                'cache': cache_block,
            })

        return jsonify({
            'status': 'ok',
            'uptime_seconds': uptime_seconds,
            'version': {
                'branch': current_app.config.get('GIT_BRANCH'),
                'commit': current_app.config.get('GIT_COMMIT'),
            },
            'clients': clients_info,
        })

    # ── Background cache warmer ───────────────────────────────────────────────
    from app.services.cache_warmer import start_scheduler
    app.cache_scheduler = start_scheduler(app)

    return app
