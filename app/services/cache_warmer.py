"""
Background cache warmer for Adobe Analytics configuration data.

Warms the cache at startup and on a 24-hour schedule so users never
hit a cold cache for slow-changing configuration data.
"""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.cache import CacheService, CONFIG_TTL_HOURS

logger = logging.getLogger(__name__)

# Cache keys that hold slow-changing configuration data (24h TTL)
CONFIG_CACHE_KEYS = {
    'dimensions',
    'events',
    'processing_rules',
    'channel_rules',
    'marketing_channels',
    'listvars',
}


def _get_api_service_v2(app):
    """Build or retrieve the API 2.0 service for a given app instance"""
    from app.services.adobe_analytics_v2 import AdobeAnalyticsV2Service
    from app.services.adobe_auth import OAuth2Auth

    if not hasattr(app, 'codex_api_service_v2'):
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
    return app.codex_api_service_v2


def _get_api_service_v14(app):
    """Build or retrieve the API 1.4 service for a given app instance"""
    from app.services.adobe_analytics import AdobeAnalyticsService

    if not hasattr(app, 'codex_api_service_v14'):
        app.codex_api_service_v14 = AdobeAnalyticsService(
            username=app.config['AW_USERNAME'],
            secret=app.config['AW_SECRET'],
        )
    return app.codex_api_service_v14


def warm_cache_key(app, rsid, cache_key):
    """Fetch and cache a single configuration key."""
    cache = CacheService()
    api_v2 = _get_api_service_v2(app)
    api_v14 = _get_api_service_v14(app)

    fetch_map = {
        'dimensions':         lambda: api_v2.get_dimensions(rsid),
        'events':             lambda: api_v2.get_success_events(rsid),
        'processing_rules':   lambda: api_v14.get_processing_rules(rsid),
        'channel_rules':      lambda: api_v14.get_marketing_channel_rules(rsid),
        'marketing_channels': lambda: api_v14.get_marketing_channels(rsid),
        'listvars':           lambda: api_v14.get_list_variables(rsid),
    }

    fetch_func = fetch_map.get(cache_key)
    if not fetch_func:
        return

    try:
        cache.get_or_set(rsid, cache_key, fetch_func, ttl_hours=CONFIG_TTL_HOURS)
        logger.info("Warmed cache key '%s' for rsid '%s'", cache_key, rsid)
    except Exception:
        logger.exception("Failed to warm cache key '%s' for rsid '%s'", cache_key, rsid)


def warm_cache(app):
    """Fetch and cache all slow-changing configuration data."""
    with app.app_context():
        rsid = app.config['AW_REPORTSUITE_ID']
        logger.info("Starting cache warm for rsid '%s'", rsid)

        for key in CONFIG_CACHE_KEYS:
            warm_cache_key(app, rsid, key)

        logger.info("Cache warm complete for rsid '%s'", rsid)


def start_scheduler(app):
    """
    Start the background scheduler that warms the cache every 24 hours.

    Guards against double-start in Flask's dev reloader by only running
    in the main Werkzeug process.
    """
    # In dev mode, Flask's reloader spawns a child process. Only start the
    # scheduler in the child (where WERKZEUG_RUN_MAIN == 'true') to avoid
    # running it twice. In production there is no reloader so the env var
    # won't be set — start unconditionally.
    is_reloader_active = os.environ.get('WERKZEUG_RUN_MAIN')
    if is_reloader_active is not None and is_reloader_active != 'true':
        return None

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: warm_cache(app),
        'interval',
        hours=24,
        id='cache_warmer',
    )
    scheduler.start()

    # Warm immediately in a background thread so the app is available right away
    import threading
    threading.Thread(target=warm_cache, args=(app,), daemon=True).start()

    logger.info("Cache warmer scheduler started (24h interval)")
    return scheduler
