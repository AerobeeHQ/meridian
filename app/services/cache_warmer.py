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
    'segments',
    'calculated_metrics',
    'launch_rules',       # v2-003: Adobe Launch rules (only populated when LAUNCH_ENABLED)
}


def warm_cache_key(app, rsid, cache_key):
    """Fetch and cache a single configuration key."""
    cache = CacheService()
    api_v2 = getattr(app, 'codex_api_service_v2', None)
    api_v14 = app.codex_api_service_v14

    api_launch = getattr(app, 'codex_launch_service', None)
    property_id = app.config.get('LAUNCH_PROPERTY_ID')

    fetch_map = {
        'processing_rules':    lambda: api_v14.get_processing_rules(rsid),
        'channel_rules':       lambda: api_v14.get_marketing_channel_rules(rsid),
        'marketing_channels':  lambda: api_v14.get_marketing_channels(rsid),
        'listvars':            lambda: api_v14.get_list_variables(rsid),
    }
    if api_v2 is not None:
        fetch_map.update({
            'dimensions':         lambda: api_v2.get_dimensions(rsid),
            'events':             lambda: api_v2.get_success_events(rsid),
            'segments':           lambda: api_v2.get_segments(rsid),
            'calculated_metrics': lambda: api_v2.get_calculated_metrics(rsid),
        })
    if api_launch is not None and property_id:
        fetch_map['launch_rules'] = lambda: api_launch.get_analytics_actions(property_id)

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
    in the child worker process (where WERKZEUG_RUN_MAIN == 'true').
    In production (no reloader), starts unconditionally.
    """
    # In dev mode (debug=True), Flask's reloader spawns a child process and sets
    # WERKZEUG_RUN_MAIN='true' in it. We skip the parent process to avoid
    # starting two schedulers. In production, debug is False so we always start.
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
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
