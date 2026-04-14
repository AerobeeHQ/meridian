"""
Background cache warmer for Adobe Analytics configuration data.

Warms the cache at startup and on a 24-hour schedule so users never
hit a cold cache for slow-changing configuration data.

For multisite: iterates all configured clients and warms each independently.
"""
import logging
import os
import threading

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
}


def warm_cache_key(client_slug: str, rsid: str, cache: CacheService, api_v2, api_v14, cache_key: str):
    """Fetch and cache a single configuration key for one client."""
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

    fetch_func = fetch_map.get(cache_key)
    if not fetch_func:
        return

    try:
        cache.get_or_set(rsid, cache_key, fetch_func, ttl_hours=CONFIG_TTL_HOURS)
        logger.info("[%s] Warmed cache key '%s'", client_slug, cache_key)
    except Exception:
        logger.exception("[%s] Failed to warm cache key '%s'", client_slug, cache_key)


def warm_client(app, client_slug: str):
    """Warm all slow-changing cache keys for a single client."""
    with app.app_context():
        ctx = app.codex_clients.get(client_slug)
        if ctx is None:
            logger.warning("warm_client called for unknown client '%s'", client_slug)
            return

        rsid    = ctx['config']['AW_REPORTSUITE_ID']
        api_v2  = ctx['api_v2']
        api_v14 = ctx['api_v14']
        cache   = ctx['cache']

        logger.info("[%s] Starting cache warm (rsid: %s)", client_slug, rsid)
        for key in CONFIG_CACHE_KEYS:
            warm_cache_key(client_slug, rsid, cache, api_v2, api_v14, key)
        logger.info("[%s] Cache warm complete", client_slug)


def warm_all_clients(app):
    """Warm caches for all configured clients."""
    for client_slug in app.codex_clients:
        warm_client(app, client_slug)


def start_scheduler(app):
    """
    Start the background scheduler that warms all client caches every 24 hours.

    Guards against double-start in Flask's dev reloader by only running
    in the child worker process (where WERKZEUG_RUN_MAIN == 'true').
    In production (no reloader), starts unconditionally.
    """
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return None

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: warm_all_clients(app),
        'interval',
        hours=24,
        id='cache_warmer',
    )
    scheduler.start()

    # Warm immediately in the background so the app is available right away.
    threading.Thread(target=warm_all_clients, args=(app,), daemon=True).start()

    logger.info("Cache warmer scheduler started (24h interval, %d client(s))", len(app.codex_clients))
    return scheduler
