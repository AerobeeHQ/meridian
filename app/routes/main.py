"""
Main routes for the Codex application
"""
import csv
import io
import json
import logging
import os
import re
import traceback as _traceback
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from flask import Blueprint, render_template, current_app, Response, request, jsonify, redirect, abort, make_response

import requests

from app.services.adobe_analytics import AdobeAnalyticsService
from app.services.adobe_analytics_v2 import AdobeAnalyticsV2Service
from app.services.adobe_auth import OAuth2Auth
from app.services.cache import CacheService, CONFIG_TTL_HOURS
from app.services import notes as notes_service


logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

# Initialize cache service
cache = CacheService()


def _render_api_error(exc: Exception, status: int = 503):
    """Render the API 1.4 error page with full traceback available for debugging.

    Args:
        exc:    The exception that caused the failure.
        status: HTTP status code to return (default 503 Service Unavailable).
    """
    tb_text = _traceback.format_exc()
    return render_template(
        '_api_error.html',
        title='API Unavailable',
        rsid=current_app.config.get('AW_REPORTSUITE_ID', ''),
        cache_info=None,
        active_tab=None,
        dimension_id=None,
        error_type=type(exc).__name__,
        error_message=str(exc),
        traceback_text=tb_text,
    ), status


@main_bp.app_errorhandler(requests.exceptions.RequestException)
def handle_api14_error(exc: requests.exceptions.RequestException):
    """Catch any unhandled requests error and show a friendly error page.

    This covers ReadTimeout, ConnectionError, HTTPError, etc. that bubble up
    from API 1.4 calls in route functions.  API 1.4 errors that are already
    caught inside ThreadPoolExecutor loops (evar_detail) don't reach here.
    """
    logger.warning("API 1.4 request failed — returning error page: %s", exc)
    return _render_api_error(exc)


@main_bp.app_context_processor
def inject_globals():
    """Inject global values into all templates"""
    # Use a sentinel to distinguish "not yet resolved" from an empty string
    suite_name = current_app.config.get('CODEX_RESOLVED_SUITE_NAME')

    if suite_name is None:
        rsid = current_app.config.get('AW_REPORTSUITE_ID', '')

        # Prefer explicit config value; fall back to API lookup (API 2.0 only)
        suite_name = current_app.config.get('REPORTSUITE_NAME')
        if not suite_name and get_api_version() == '2.0':
            try:
                svc = get_api_service()
                suite_name = svc.get_report_suite_name(rsid)
            except Exception:
                logger.warning("Could not resolve suite name for %s; falling back to RSID", rsid)
                suite_name = rsid
        suite_name = suite_name or rsid

        # Cache on the app object so subsequent requests skip the API call
        current_app.config['CODEX_RESOLVED_SUITE_NAME'] = suite_name

    return {
        'git_branch': current_app.config.get('GIT_BRANCH'),
        'git_commit': current_app.config.get('GIT_COMMIT'),
        'suite_name': suite_name,
        'app_title': current_app.config.get('APP_TITLE', ''),
    }


def get_api_version() -> str:
    """Get configured API version (default: 2.0)"""
    return current_app.config.get('API_VERSION', '2.0')


def get_api_service():
    """
    Get configured Adobe Analytics service based on API_VERSION config.

    Service instances are stored on the Flask app object so each
    ``create_app()`` call gets its own instance (avoids stale state
    when the factory is called multiple times, e.g. in tests).

    Returns:
        AdobeAnalyticsV2Service for API 2.0, or AdobeAnalyticsService for 1.4
    """
    app = current_app._get_current_object()
    api_version = get_api_version()

    if api_version == '2.0':
        if not hasattr(app, 'codex_api_service_v2'):
            auth = OAuth2Auth(
                client_id=current_app.config['CLIENT_ID'],
                client_secret=current_app.config['CLIENT_SECRET'],
                scopes=current_app.config.get('SCOPES')
            )
            app.codex_api_service_v2 = AdobeAnalyticsV2Service(
                auth_service=auth,
                client_id=current_app.config['CLIENT_ID'],
                org_id=current_app.config['ORGANIZATION_ID']
            )
        return app.codex_api_service_v2
    else:
        # API 1.4 (legacy)
        return get_api_service_v14()


def get_api_service_v14() -> AdobeAnalyticsService:
    """
    Get API 1.4 service (used for processing rules which aren't in 2.0).

    Stored on the app instance for the same reason as ``get_api_service``.

    Returns:
        AdobeAnalyticsService configured for API 1.4
    """
    app = current_app._get_current_object()

    if not hasattr(app, 'codex_api_service_v14'):
        app.codex_api_service_v14 = AdobeAnalyticsService(
            username=current_app.config['AW_USERNAME'],
            secret=current_app.config['AW_SECRET'],
            request_timeout=current_app.config.get('API_V14_TIMEOUT', 5.0),
        )
    return app.codex_api_service_v14


def get_rsid() -> str:
    """Get configured report suite ID"""
    return current_app.config['AW_REPORTSUITE_ID']


def get_cached_data(key: str, fetch_func, ttl_hours: float = None):
    """Get data from cache or fetch from API.

    Args:
        key: Cache key name
        fetch_func: Callable that fetches fresh data on cache miss
        ttl_hours: Optional TTL override (default uses CacheService default)
    """
    rsid = get_rsid()
    kwargs = {}
    if ttl_hours is not None:
        kwargs['ttl_hours'] = ttl_hours
    return cache.get_or_set(rsid, key, fetch_func, **kwargs)


def get_cache_info() -> dict:
    """Get cache information for footer"""
    rsid = get_rsid()
    return cache.get_info(rsid)


def render_listing(title, data, columns, active_tab, monospace_columns=None, column_styles=None, dt_order=None, column_badges=None, preformatted_columns=None, **kwargs):
    """Render listing.html with common context variables injected automatically.

    Args:
        title: Page title shown in the browser tab and heading.
        data: List of row dicts to display in the table.
        columns: Ordered list of column header strings.
        active_tab: Nav-tab identifier used to highlight the current section.
        monospace_columns: Column names whose cells should be styled monospace.
        column_styles: Dict mapping column names to inline CSS style strings.
        **kwargs: Extra variables forwarded to the template (e.g. cache_key).
    """
    return render_template(
        'listing.html',
        title=title,
        data=data,
        columns=columns,
        rsid=get_rsid(),
        cache_info=get_cache_info(),
        active_tab=active_tab,
        monospace_columns=monospace_columns or [],
        column_styles=column_styles or {},
        dt_order=dt_order or [],
        column_badges=column_badges or {},
        preformatted_columns=preformatted_columns or [],
        **kwargs
    )


def safe_extract_dimension_number(dim_id: str, prefix: str) -> int:
    """
    Safely extract numeric suffix from a dimension ID.

    Args:
        dim_id: Dimension ID (e.g., 'prop1', 'evar42', 'event10')
        prefix: Expected prefix to remove (e.g., 'prop', 'evar', 'event')

    Returns:
        Numeric suffix as integer, or 999 if parsing fails

    Examples:
        >>> safe_extract_dimension_number('prop1', 'prop')
        1
        >>> safe_extract_dimension_number('evar42', 'evar')
        42
        >>> safe_extract_dimension_number('invalid', 'prop')
        999
    """
    try:
        cleaned = dim_id.replace(prefix, '')
        return int(cleaned) if cleaned else 999
    except (ValueError, AttributeError):
        return 999


def format_conditions(text: str) -> str:
    """Format a processing rule conditions string for readability.

    Replaces ' AND ' separators with newlines so each condition clause
    appears on its own line when rendered in a <pre> block.
    """
    if not text:
        return text
    return text.replace(' AND ', '\nAND ')


def find_related_processing_rules(rules: list[dict], *terms: str) -> list[dict]:
    """Return processing rules whose conditions or actions reference any of the
    given dimension terms.

    Uses whole-word, case-insensitive matching so that e.g. ``prop1`` does not
    accidentally match ``prop10`` or ``prop100``.

    Args:
        rules: Cached list of processing rule dicts from ``get_processing_rules()``.
        *terms: One or more dimension identifiers to search for
                (e.g. ``'evar5'``, or ``'list1', 'listvar1'``).

    Returns:
        Subset of ``rules`` that reference at least one of the given terms.
    """
    if not rules or not terms:
        return []
    safe_terms = [t for t in terms if t]
    if not safe_terms:
        return []
    pattern = re.compile(
        r'\b(' + '|'.join(re.escape(t) for t in safe_terms) + r')\b',
        re.IGNORECASE,
    )
    return [
        rule for rule in rules
        if pattern.search(rule.get('rules', '') or '')
        or pattern.search(rule.get('actions', '') or '')
    ]


def _parse_segment_schema(schema: list[str]) -> dict:
    """Convert the flat compatibility schema list into readable grouped labels.

    Schema entries look like:
        'attribute_variables/evar22'  → eVar22 (attribute)
        'event_metrics/event21'       → event21 (event)
        'container_hits'              → hits (container scope)

    Returns a dict with keys 'container', 'variables', and 'events'.
    """
    container = ''
    variables = []
    events = []

    for entry in schema:
        if entry.startswith('container_'):
            container = entry.replace('container_', '')
        elif '_variables/' in entry:
            # e.g. 'attribute_variables/evar22' → 'evar22'
            var_id = entry.split('/')[-1]
            variables.append(var_id)
        elif '_metrics/' in entry:
            # e.g. 'event_metrics/event21' → 'event21'
            metric_id = entry.split('/')[-1]
            events.append(metric_id)

    return {'container': container, 'variables': variables, 'events': events}


def _walk_formula(node: Any, metrics: set, segments: set) -> None:
    """Recursively walk a calculated metric formula tree collecting references.

    Extracted items:
    - metrics:  set of (metric_id, description) tuples  e.g. ('metrics/visits', 'Visits')
    - segments: set of (segment_id, description) tuples e.g. ('s200000529_abc', 'My segment')
    """
    if not isinstance(node, dict):
        return
    func = node.get("func", "")
    if func == "metric":
        name = node.get("name", "")
        desc = node.get("description", "")
        if name:
            metrics.add((name, desc))
    elif func == "segment-ref":
        seg_id = node.get("id", "")
        desc = node.get("description", "")
        if seg_id:
            segments.add((seg_id, desc))
    else:
        for value in node.values():
            if isinstance(value, dict):
                _walk_formula(value, metrics, segments)
            elif isinstance(value, list):
                for item in value:
                    _walk_formula(item, metrics, segments)


def _parse_calc_metric_formula(definition: dict) -> dict:
    """Return sorted lists of referenced metrics and segments from a formula.

    Returns:
        {'metrics': [(id, desc), ...], 'segments': [(id, desc), ...]}
    """
    metrics: set = set()
    segments: set = set()
    _walk_formula(definition, metrics, segments)
    return {
        "metrics": sorted(metrics, key=lambda x: x[0]),
        "segments": sorted(segments, key=lambda x: x[1].lower()),
    }


# Column mappings matching server.R transformations
PROPS_COLUMNS = {
    'id': 'Prop',
    'name': 'Label',
    'pathing_enabled': 'Pathing',
    'list_enabled': 'List Support',
    'list_delimiter': 'Delimiter',
    'description': 'Description'
}

EVARS_COLUMNS = {
    'id': 'eVar',
    'name': 'Label',
    'type': 'Type',
    'expiration_type': 'Expiration',
    'allocation_type': 'Allocation',
    'description': 'Description'
}

EVENTS_COLUMNS = {
    'id': 'Event',
    'name': 'Label',
    'type': 'Type',
    'serialization': 'Serialisation',
    'description': 'Description'
}

LISTVARS_COLUMNS = {
    'name': 'ListVar',
    'allocation_type': 'Allocation',
    'enabled': 'Enabled',
    'value_delimiter': 'Delimiter',
    'max_values': 'Max',
    'id': 'ID',
    'expiration_custom_days': 'Expiry Days',
    'expiration_type': 'Expiry Type',
    'description': 'Description'
}

CORE_COLUMNS = {
    'id': 'Dimension',
    'name': 'Label',
    'type': 'Type',
    'description': 'Description'
}

PROCRULES_COLUMNS = {
    'ruleNum': 'Rule',
    'title': 'Section',
    'rules': 'Conditions',
    'matchOn': 'Match Type',
    'actions': 'Actions',
    'comment': 'Comments'
}

MKTCHANNELS_COLUMNS = {
    'name': 'Marketing Channel Name',
    'channel_id': 'Channel ID',
    'enabled': 'Enabled',
    'override_last_touch_channel': 'Override Last Touch Channel'
}

MKTRULES_COLUMNS = {
    'ruleset': 'Ruleset',
    'channel_id': 'Channel ID',
    'junction': 'Junction',
    'type': 'Type',
    'id': 'ID',
    'query_string': 'Query String',
    'rule_id': 'Rule ID',
    'hit_attribute': 'Hit Attribute',
    'hit_query_param': 'Hit Query Param',
    'operator': 'Operator',
    'matches': 'Matches'
}

SEGMENTS_COLUMNS = {
    'name': 'Name',
    'owner': 'Owner',
    'modified': 'Modified',
    'tags': 'Tags',
    'description': 'Description',
}

CALC_METRICS_COLUMNS = {
    'name': 'Name',
    'type': 'Type',
    'owner': 'Owner',
    'modified': 'Modified',
    'tags': 'Tags',
    'description': 'Description',
}


def transform_data(raw_data: list, column_mapping: dict) -> list[dict]:
    """Transform raw API data to display format with renamed columns"""
    transformed = []
    for item in raw_data:
        row = {}
        for api_key, display_name in column_mapping.items():
            row[display_name] = item.get(api_key, '')
        transformed.append(row)
    return transformed


def generate_csv(data: list[dict], filename: str) -> Response:
    """Generate CSV download response"""
    if not data:
        return Response("No data available", mimetype='text/plain')

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
    return response


# Define core dimension IDs (out-of-the-box dimensions)
CORE_DIMENSION_IDS = [
    'variables/page',
    'variables/pageurl',
    'variables/sitesection',
    'variables/server',
    'variables/channel',
    'variables/customlink',
    'variables/downloadlink',
    'variables/exitlink',
    'variables/product',
    'variables/referrer',
    'variables/campaign',
    'variables/searchengine'
]


# =============================================================================
# Overview Route
# =============================================================================

def _relative_time(iso_str):
    """Convert an ISO timestamp string to a human-readable relative time."""
    if not iso_str:
        return ''
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return 'just now'
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
    except (ValueError, TypeError):
        return ''


@main_bp.route('/')
@main_bp.route('/overview')
def overview():
    """Report suite summary overview page"""
    rsid = get_rsid()

    # Read from cache only — do not trigger API calls on the overview page
    # Keep raw values (None = not yet cached) to track per-stat availability
    _dimensions_raw        = cache.get(rsid, 'dimensions')
    _events_raw            = cache.get(rsid, 'events')
    _listvars_raw          = cache.get(rsid, 'listvars')
    _processing_rules_raw  = cache.get(rsid, 'processing_rules')
    _marketing_channels_raw = cache.get(rsid, 'marketing_channels')
    _segments_raw          = cache.get(rsid, 'segments')
    _calc_metrics_raw      = cache.get(rsid, 'calculated_metrics')

    dimensions         = _dimensions_raw or []
    raw_events         = _events_raw or []
    processing_rules   = _processing_rules_raw or []
    marketing_channels = _marketing_channels_raw or []
    listvars           = _listvars_raw or []
    segments           = _segments_raw or []
    calc_metrics       = _calc_metrics_raw or []

    # Count configured eVars and props (exclude classifications which have a dot in the id)
    evars = [
        d for d in dimensions
        if d.get('id', '').startswith('variables/evar')
        and '.' not in d.get('id', '').replace('variables/', '')
    ]
    props = [
        d for d in dimensions
        if d.get('id', '').startswith('variables/prop')
        and '.' not in d.get('id', '').replace('variables/', '')
    ]

    stats = {
        'props':    {'count': len(props),            'total': 75,   'available': _dimensions_raw is not None},
        'evars':    {'count': len(evars),             'total': 250,  'available': _dimensions_raw is not None},
        'events':   {'count': len(raw_events),        'total': 1000, 'available': _events_raw is not None},
        'listvars': {'count': len(listvars),          'total': 3,    'available': _listvars_raw is not None},
        'segments':        {'count': len(segments),      'available': _segments_raw is not None},
        'calc_metrics':    {'count': len(calc_metrics),  'available': _calc_metrics_raw is not None},
        'processing_rules':   {'count': len(processing_rules),   'available': _processing_rules_raw is not None},
        'marketing_channels': {'count': len(marketing_channels), 'available': _marketing_channels_raw is not None},
        'cache_populated': _dimensions_raw is not None,
    }

    # Recent notes activity — scan notes dir for files belonging to this rsid
    recent_notes = []
    notes_dir = notes_service.NOTES_DIR
    safe_rsid = rsid.replace('/', '_').replace('\\', '_')
    type_to_route = {'prop': 'props', 'evar': 'evars', 'event': 'events', 'listvar': 'listvars'}

    if os.path.exists(notes_dir):
        candidates = []
        for filename in os.listdir(notes_dir):
            if not filename.startswith(safe_rsid + '_') or not filename.endswith('.json'):
                continue
            filepath = os.path.join(notes_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    note = json.load(f)
                updated_at = note.get('updated_at', '')
                if not updated_at:
                    continue
                # Parse "rsid_type_id.json" → type and id
                remainder = filename[len(safe_rsid) + 1:-5]  # strip prefix and .json
                parts = remainder.split('_', 1)
                dim_type = parts[0] if parts else ''
                dim_id = parts[1] if len(parts) > 1 else remainder
                candidates.append({
                    'type': dim_type,
                    'id': dim_id,
                    'route': type_to_route.get(dim_type, dim_type + 's'),
                    'updated_at': updated_at,
                    'relative_time': _relative_time(updated_at),
                    'description': note.get('plain_description', ''),
                })
            except (json.JSONDecodeError, IOError):
                continue
        recent_notes = sorted(candidates, key=lambda x: x['updated_at'], reverse=True)[:5]

    response = make_response(render_template(
        'overview.html',
        title='Overview',
        rsid=rsid,
        stats=stats,
        recent_notes=recent_notes,
        cache_info=get_cache_info(),
        active_tab='overview',
    ))
    response.headers['Cache-Control'] = 'no-store'
    return response


@main_bp.route('/core')
def core():
    """Display core/out-of-the-box dimensions"""
    api = get_api_service()
    rsid = get_rsid()

    # Cache raw dimensions for reuse
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid), ttl_hours=CONFIG_TTL_HOURS)

    # Filter core dimensions
    raw_core = []
    for dim in raw_dimensions:
        dim_id = dim.get("id", "")
        if dim_id in CORE_DIMENSION_IDS:
            # Transform to simpler format
            core_item = {
                'id': dim_id.replace("variables/", ""),
                'name': dim.get("name") or dim.get("title", ""),
                'type': dim.get("type", ""),
                'description': dim.get("description", "")
            }
            raw_core.append(core_item)

    # Sort by the order defined in CORE_DIMENSION_IDS
    def sort_key(item):
        full_id = f"variables/{item['id']}"
        try:
            return CORE_DIMENSION_IDS.index(full_id)
        except ValueError:
            return 999

    raw_core.sort(key=sort_key)

    data = transform_data(raw_core, CORE_COLUMNS)

    return render_listing('Core', data, list(CORE_COLUMNS.values()), 'core', cache_key='dimensions')


@main_bp.route('/core/export')
def core_export():
    """Export core dimensions as CSV"""
    api = get_api_service()
    rsid = get_rsid()

    # Use cached dimensions
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid), ttl_hours=CONFIG_TTL_HOURS)
    raw_core = []
    for dim in raw_dimensions:
        dim_id = dim.get("id", "")
        if dim_id in CORE_DIMENSION_IDS:
            core_item = {
                'id': dim_id.replace("variables/", ""),
                'name': dim.get("name") or dim.get("title", ""),
                'type': dim.get("type", ""),
                'description': dim.get("description", "")
            }
            raw_core.append(core_item)

    # Sort by the order defined in CORE_DIMENSION_IDS
    def sort_key(item):
        full_id = f"variables/{item['id']}"
        try:
            return CORE_DIMENSION_IDS.index(full_id)
        except ValueError:
            return 999

    raw_core.sort(key=sort_key)

    data = transform_data(raw_core, CORE_COLUMNS)

    return generate_csv(data, f'{rsid}_core.csv')


@main_bp.route('/core/<dimension_id>')
def core_detail(dimension_id: str):
    """Display detail page for a specific core dimension"""
    api = get_api_service()
    rsid = get_rsid()

    # Normalize dimension_id to API format
    full_dimension_id = f"variables/{dimension_id}" if not dimension_id.startswith("variables/") else dimension_id
    display_id = dimension_id.replace("variables/", "")

    # Quick Win #1: Try to get dimension from already-cached dimensions list
    cached_dimensions = cache.get(rsid, 'dimensions')

    def fetch_dimension():
        if cached_dimensions:
            for dim in cached_dimensions:
                if dim.get("id") == full_dimension_id:
                    return dim
        return api.get_dimension(rsid, full_dimension_id)

    def fetch_top_items():
        return api.get_top_items(rsid, full_dimension_id, metric="occurrences", limit=10, days=30)

    def fetch_trend():
        return api.get_dimension_trend(rsid, full_dimension_id, metric="occurrences", days=30)

    # Quick Win #2: Check cache first, then parallelize needed API calls
    dimension = cache.get(rsid, f'core_detail_{display_id}')
    top_items = cache.get(rsid, f'core_top_{display_id}')
    trend_data = cache.get(rsid, f'core_trend_{display_id}')

    tasks = {}
    if dimension is None:
        tasks['dimension'] = fetch_dimension
    if top_items is None:
        tasks['top_items'] = fetch_top_items
    if trend_data is None:
        tasks['trend_data'] = fetch_trend

    # Execute needed fetches in parallel
    if tasks:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(func): key for key, func in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                value = future.result()
                if key == 'dimension':
                    cache.set(rsid, f'core_detail_{display_id}', value)
                    dimension = value
                elif key == 'top_items':
                    cache.set(rsid, f'core_top_{display_id}', value)
                    top_items = value
                elif key == 'trend_data':
                    cache.set(rsid, f'core_trend_{display_id}', value)
                    trend_data = value

    # Find classifications for this dimension (dimensions with parent = this dimension's ID)
    classifications = []
    if cached_dimensions:
        for dim in cached_dimensions:
            if dim.get("parent") == full_dimension_id:
                classifications.append({
                    'id': dim.get("id", "").replace("variables/", ""),
                    'name': dim.get("name") or dim.get("title", ""),
                    'description': dim.get("description", "")
                })
        # Sort classifications alphabetically by name
        classifications.sort(key=lambda x: x.get("name", "").lower())

    return render_template(
        'detail.html',
        title=f'{display_id}: {dimension.get("name", "")}',
        dimension=dimension,
        dimension_id=display_id,
        dimension_type='core',
        dimension_type_label='Core Dimension',
        top_items=top_items,
        trend_data=trend_data,
        classifications=classifications,
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='core',
        back_url='/core',
        back_label='Back to Core Listing',
        cache_key='dimensions'
    )


@main_bp.route('/props')
def props():
    """Display traffic variables (props)"""
    api = get_api_service()
    rsid = get_rsid()

    # Cache raw dimensions for reuse by detail pages (Quick Win #1)
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid), ttl_hours=CONFIG_TTL_HOURS)
    
    # Filter props from dimensions and transform
    # Exclude classifications (IDs containing a dot after the prop number, e.g., prop12.screen-height)
    raw_props = []
    for dim in raw_dimensions:
        dim_id = dim.get("id", "")
        if dim_id.startswith("variables/prop"):
            # Check if this is a classification (has a dot after prop number)
            prop_part = dim_id.replace("variables/", "")
            if "." not in prop_part:
                raw_props.append(api._transform_dimension_to_prop(dim))
    
    # Sort by prop number
    raw_props.sort(key=lambda x: api._extract_number(x.get("id", "")))
    
    data = transform_data(raw_props, PROPS_COLUMNS)

    return render_listing('Props', data, list(PROPS_COLUMNS.values()), 'props', cache_key='dimensions')


@main_bp.route('/props/export')
def props_export():
    """Export props as CSV"""
    api = get_api_service()
    rsid = get_rsid()

    # Use cached dimensions
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid), ttl_hours=CONFIG_TTL_HOURS)
    raw_props = []
    for dim in raw_dimensions:
        dim_id = dim.get("id", "")
        if dim_id.startswith("variables/prop"):
            # Exclude classifications (IDs containing a dot after prop number)
            prop_part = dim_id.replace("variables/", "")
            if "." not in prop_part:
                raw_props.append(api._transform_dimension_to_prop(dim))
    raw_props.sort(key=lambda x: api._extract_number(x.get("id", "")))
    
    data = transform_data(raw_props, PROPS_COLUMNS)

    return generate_csv(data, f'{rsid}_props.csv')


@main_bp.route('/props/<prop_id>')
def prop_detail(prop_id: str):
    """Display detail page for a specific prop"""
    api = get_api_service()
    rsid = get_rsid()

    # Normalize prop_id to API format (e.g., 'prop1' -> 'variables/prop1')
    dimension_id = f"variables/{prop_id}" if not prop_id.startswith("variables/") else prop_id
    display_id = prop_id.replace("variables/", "")

    # Quick Win #1: Try to get dimension from already-cached dimensions list
    cached_dimensions = cache.get(rsid, 'dimensions')
    
    def fetch_dimension():
        if cached_dimensions:
            for dim in cached_dimensions:
                if dim.get("id") == dimension_id:
                    return dim
        return api.get_dimension(rsid, dimension_id)

    def fetch_top_items():
        return api.get_top_items(rsid, dimension_id, metric="occurrences", limit=10, days=30)

    def fetch_trend():
        return api.get_dimension_trend(rsid, dimension_id, metric="occurrences", days=30)

    # Quick Win #2: Check cache first, then parallelize needed API calls
    dimension = cache.get(rsid, f'prop_detail_{display_id}')
    top_items = cache.get(rsid, f'prop_top_{display_id}')
    trend_data = cache.get(rsid, f'prop_trend_{display_id}')

    tasks = {}
    if dimension is None:
        tasks['dimension'] = fetch_dimension
    if top_items is None:
        tasks['top_items'] = fetch_top_items
    if trend_data is None:
        tasks['trend_data'] = fetch_trend

    # Execute needed fetches in parallel
    if tasks:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(func): key for key, func in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                value = future.result()
                if key == 'dimension':
                    cache.set(rsid, f'prop_detail_{display_id}', value)
                    dimension = value
                elif key == 'top_items':
                    cache.set(rsid, f'prop_top_{display_id}', value)
                    top_items = value
                elif key == 'trend_data':
                    cache.set(rsid, f'prop_trend_{display_id}', value)
                    trend_data = value

    # Find classifications for this prop (dimensions with parent = this dimension's ID)
    classifications = []
    if cached_dimensions:
        for dim in cached_dimensions:
            if dim.get("parent") == dimension_id:
                classifications.append({
                    'id': dim.get("id", "").replace("variables/", ""),
                    'name': dim.get("name") or dim.get("title", ""),
                    'description': dim.get("description", "")
                })
        # Sort classifications alphabetically by name
        classifications.sort(key=lambda x: x.get("name", "").lower())

    return render_template(
        'detail.html',
        title=f'{display_id}: {dimension.get("name", "")}',
        dimension=dimension,
        dimension_id=display_id,
        dimension_type='prop',
        dimension_type_label='Traffic Variable (Prop)',
        top_items=top_items,
        trend_data=trend_data,
        classifications=classifications,
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='props',
        back_url='/props',
        back_label='Back to Props Listing',
        cache_key='dimensions'
    )


@main_bp.route('/evars')
def evars():
    """Display conversion variables (eVars)"""
    api = get_api_service()
    rsid = get_rsid()

    # Cache raw dimensions for reuse by detail pages (Quick Win #1)
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid), ttl_hours=CONFIG_TTL_HOURS)
    
    # Filter eVars from dimensions and transform
    # Exclude classifications (IDs containing a dot after the evar number, e.g., evar101.catalogue-name)
    # NOTE: API 2.0 dimensions don't include allocation/expiration fields, so these columns
    # will be empty in the table view. Full configuration (including allocation, expiration,
    # and merchandising) is available on the eVar detail pages via API 1.4.
    raw_evars = []
    for dim in raw_dimensions:
        dim_id = dim.get("id", "")
        if dim_id.startswith("variables/evar"):
            # Check if this is a classification (has a dot after evar number)
            evar_part = dim_id.replace("variables/", "")
            if "." not in evar_part:
                raw_evars.append(api._transform_dimension_to_evar(dim))
    
    # Sort by evar number
    raw_evars.sort(key=lambda x: api._extract_number(x.get("id", "")))
    
    data = transform_data(raw_evars, EVARS_COLUMNS)

    return render_listing('eVars', data, list(EVARS_COLUMNS.values()), 'evars', cache_key='dimensions')


@main_bp.route('/evars/export')
def evars_export():
    """Export eVars as CSV"""
    api = get_api_service()
    rsid = get_rsid()

    # Use cached dimensions
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid), ttl_hours=CONFIG_TTL_HOURS)
    raw_evars = []
    for dim in raw_dimensions:
        dim_id = dim.get("id", "")
        if dim_id.startswith("variables/evar"):
            # Exclude classifications (IDs containing a dot after evar number)
            evar_part = dim_id.replace("variables/", "")
            if "." not in evar_part:
                raw_evars.append(api._transform_dimension_to_evar(dim))
    raw_evars.sort(key=lambda x: api._extract_number(x.get("id", "")))
    
    data = transform_data(raw_evars, EVARS_COLUMNS)

    return generate_csv(data, f'{rsid}_evars.csv')


@main_bp.route('/evars/<evar_id>')
def evar_detail(evar_id: str):
    """Display detail page for a specific eVar"""
    api = get_api_service()
    api_v14 = get_api_service_v14()
    rsid = get_rsid()

    # Normalize evar_id to API format
    dimension_id = f"variables/{evar_id}" if not evar_id.startswith("variables/") else evar_id
    display_id = evar_id.replace("variables/", "")

    # Quick Win #1: Try to get dimension from already-cached dimensions list
    cached_dimensions = cache.get(rsid, 'dimensions')
    
    def fetch_dimension():
        if cached_dimensions:
            for dim in cached_dimensions:
                if dim.get("id") == dimension_id:
                    return dim
        return api.get_dimension(rsid, dimension_id)

    def fetch_evar_config():
        """Fetch eVar configuration from API 1.4 (has allocation, expiration, merchandising)"""
        return api_v14.get_evar(rsid, display_id)

    def fetch_top_items():
        return api.get_top_items(rsid, dimension_id, metric="occurrences", limit=10, days=30)

    def fetch_trend():
        return api.get_dimension_trend(rsid, dimension_id, metric="occurrences", days=30)

    # Quick Win #2: Check cache first, then parallelize needed API calls
    dimension = cache.get(rsid, f'evar_detail_{display_id}')
    evar_config = cache.get(rsid, f'evar_config_{display_id}')
    top_items = cache.get(rsid, f'evar_top_{display_id}')
    trend_data = cache.get(rsid, f'evar_trend_{display_id}')

    tasks = {}
    if dimension is None:
        tasks['dimension'] = fetch_dimension
    if evar_config is None:
        tasks['evar_config'] = fetch_evar_config
    if top_items is None:
        tasks['top_items'] = fetch_top_items
    if trend_data is None:
        tasks['trend_data'] = fetch_trend

    if tasks:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(func): key for key, func in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    value = future.result()
                except Exception as exc:
                    logger.warning(
                        "evar_detail: failed to fetch '%s' for %s — %s",
                        key, display_id, exc,
                    )
                    value = None
                # Only cache successful results; a None value means the API
                # was unavailable and we want to retry on the next request.
                if value is None:
                    continue
                if key == 'dimension':
                    cache.set(rsid, f'evar_detail_{display_id}', value)
                    dimension = value
                elif key == 'evar_config':
                    cache.set(rsid, f'evar_config_{display_id}', value)
                    evar_config = value
                elif key == 'top_items':
                    cache.set(rsid, f'evar_top_{display_id}', value)
                    top_items = value
                elif key == 'trend_data':
                    cache.set(rsid, f'evar_trend_{display_id}', value)
                    trend_data = value

    # Parse expiration & allocation from the API 2.0 description field.
    # This avoids dependence on API 1.4 (deprecated August 2026).
    dimension = dimension.copy() if dimension else {}
    parsed = AdobeAnalyticsV2Service.parse_description_metadata(dimension.get('description', ''))
    if parsed['expiration_type']:
        dimension['expiration_type'] = parsed['expiration_type']
    if parsed['expiration_custom_days']:
        dimension['expiration_custom_days'] = parsed['expiration_custom_days']
    if parsed['allocation_type']:
        dimension['allocation_type'] = parsed['allocation_type']

    # Fallback: merge API 1.4 data for fields not available from API 2.0
    # (merchandising_syntax, binding_events, enabled).
    # Also backfill expiration/allocation if the description didn't contain them.
    if evar_config:
        if not dimension.get('expiration_type'):
            dimension['expiration_type'] = str(evar_config.get('expiration_type', ''))
        if not dimension.get('expiration_custom_days'):
            dimension['expiration_custom_days'] = evar_config.get('expiration_custom_days')
        if not dimension.get('allocation_type'):
            dimension['allocation_type'] = evar_config.get('allocation_type')
        dimension.setdefault('merchandising_syntax', evar_config.get('merchandising_syntax'))
        dimension.setdefault('binding_events', evar_config.get('binding_events'))
        dimension.setdefault('enabled', evar_config.get('enabled'))

    # Find classifications for this eVar (dimensions with parent = this dimension's ID)
    classifications = []
    if cached_dimensions:
        for dim in cached_dimensions:
            if dim.get("parent") == dimension_id:
                classifications.append({
                    'id': dim.get("id", "").replace("variables/", ""),
                    'name': dim.get("name") or dim.get("title", ""),
                    'description': dim.get("description", "")
                })
        # Sort classifications alphabetically by name
        classifications.sort(key=lambda x: x.get("name", "").lower())

    return render_template(
        'detail.html',
        title=f'{display_id}: {dimension.get("name", "")}',
        dimension=dimension,
        dimension_id=display_id,
        dimension_type='evar',
        dimension_type_label='Conversion Variable (eVar)',
        top_items=top_items,
        trend_data=trend_data,
        classifications=classifications,
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='evars',
        back_url='/evars',
        back_label='Back to eVars Listing',
        cache_key='dimensions'
    )


@main_bp.route('/events')
def events():
    """Display success events"""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data('events', lambda: api.get_success_events(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, EVENTS_COLUMNS)

    return render_listing('Events', data, list(EVENTS_COLUMNS.values()), 'events', cache_key='events')


@main_bp.route('/events/export')
def events_export():
    """Export events as CSV"""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data('events', lambda: api.get_success_events(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, EVENTS_COLUMNS)

    return generate_csv(data, f'{rsid}_events.csv')


@main_bp.route('/events/<event_id>')
def event_detail(event_id: str):
    """Display detail page for a specific event"""
    api = get_api_service()
    rsid = get_rsid()

    # Normalize event_id to API format (e.g., 'event1' -> 'metrics/event1')
    metric_id = f"metrics/{event_id}" if not event_id.startswith("metrics/") else event_id
    display_id = event_id.replace("metrics/", "")

    # Try to get metric from already-cached metrics list
    cached_metrics = cache.get(rsid, 'metrics')

    def fetch_metric():
        if cached_metrics:
            for metric in cached_metrics:
                if metric.get("id") == metric_id:
                    return metric
        return api.get_metric(rsid, metric_id)

    def fetch_trend():
        return api.get_event_trend(rsid, metric_id, days=30)

    # Check cache first, then parallelize needed API calls
    metric = cache.get(rsid, f'event_detail_{display_id}')
    trend_data = cache.get(rsid, f'event_trend_{display_id}')

    tasks = {}
    if metric is None:
        tasks['metric'] = fetch_metric
    if trend_data is None:
        tasks['trend_data'] = fetch_trend

    # Execute needed fetches in parallel
    if tasks:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(func): key for key, func in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                value = future.result()
                if key == 'metric':
                    cache.set(rsid, f'event_detail_{display_id}', value)
                    metric = value
                elif key == 'trend_data':
                    cache.set(rsid, f'event_trend_{display_id}', value)
                    trend_data = value

    return render_template(
        'event_detail.html',
        title=f'{display_id}: {metric.get("name", "")}',
        metric=metric,
        event_id=display_id,
        trend_data=trend_data,
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='events',
        back_url='/events',
        back_label='Back to Events Listing',
        cache_key='events'
    )


@main_bp.route('/listvars')
def listvars():
    """Display list variables (uses API 1.4 for full config data)"""
    # List variable config is better exposed in API 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('listvars', lambda: api.get_list_variables(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, LISTVARS_COLUMNS)

    return render_listing('ListVars', data, list(LISTVARS_COLUMNS.values()), 'listvars', cache_key='listvars')


@main_bp.route('/listvars/export')
def listvars_export():
    """Export list variables as CSV (uses API 1.4)"""
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('listvars', lambda: api.get_list_variables(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, LISTVARS_COLUMNS)

    return generate_csv(data, f'{rsid}_listvars.csv')


@main_bp.route('/listvars/<listvar_name>')
def listvar_detail(listvar_name: str):
    """Display detail page for a specific list variable"""
    api_v14 = get_api_service_v14()
    api_v2 = get_api_service()
    rsid = get_rsid()

    # ListVar names are like "List Var 1", "List Var 2", etc.
    # The API 2.0 dimension ID is like "variables/listvar1"
    # Extract number from name to build dimension ID
    listvar_match = re.search(r'(\d+)$', listvar_name.replace(' ', ''))
    listvar_num = listvar_match.group(1) if listvar_match else '1'
    dimension_id = f"variables/listvar{listvar_num}"

    # Get listvar config from cached API 1.4 data
    cached_listvars = cache.get(rsid, 'listvars')

    def fetch_listvar():
        if cached_listvars:
            for lv in cached_listvars:
                if lv.get("name") == listvar_name:
                    return lv
        # Fetch fresh if not cached
        listvars = api_v14.get_list_variables(rsid)
        for lv in listvars:
            if lv.get("name") == listvar_name:
                return lv
        return {}

    def fetch_top_items():
        return api_v2.get_top_items(rsid, dimension_id, metric="occurrences", limit=10, days=30)

    def fetch_trend():
        return api_v2.get_dimension_trend(rsid, dimension_id, metric="occurrences", days=30)

    # Check cache first, then parallelize needed API calls
    listvar = cache.get(rsid, f'listvar_detail_{listvar_num}')
    top_items = cache.get(rsid, f'listvar_top_{listvar_num}')
    trend_data = cache.get(rsid, f'listvar_trend_{listvar_num}')

    tasks = {}
    if listvar is None:
        tasks['listvar'] = fetch_listvar
    if top_items is None:
        tasks['top_items'] = fetch_top_items
    if trend_data is None:
        tasks['trend_data'] = fetch_trend

    # Execute needed fetches in parallel
    if tasks:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(func): key for key, func in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    value = future.result()
                except Exception:
                    value = {} if key == 'listvar' else []
                if key == 'listvar':
                    cache.set(rsid, f'listvar_detail_{listvar_num}', value)
                    listvar = value
                elif key == 'top_items':
                    cache.set(rsid, f'listvar_top_{listvar_num}', value)
                    top_items = value
                elif key == 'trend_data':
                    cache.set(rsid, f'listvar_trend_{listvar_num}', value)
                    trend_data = value

    return render_template(
        'listvar_detail.html',
        title=f'{listvar_name}',
        listvar=listvar or {},
        listvar_name=listvar_name,
        listvar_num=listvar_num,
        top_items=top_items or [],
        trend_data=trend_data or {},
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='listvars',
        back_url='/listvars',
        back_label='Back to ListVars Listing',
        cache_key='listvars'
    )


@main_bp.route('/processing-rules')
def processing_rules():
    """Display processing rules (always uses API 1.4 - not available in 2.0)"""
    # Processing rules are NOT available in API 2.0, so we always use 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('processing_rules', lambda: api.get_processing_rules(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, PROCRULES_COLUMNS)
    for row in data:
        if row.get('Conditions'):
            row['Conditions'] = format_conditions(row['Conditions'])

    return render_listing(
        'Proc Rules', data, list(PROCRULES_COLUMNS.values()), 'processing-rules',
        monospace_columns=['Actions'],
        preformatted_columns=['Conditions'],
        cache_key='processing_rules'
    )


@main_bp.route('/processing-rules/export')
def processing_rules_export():
    """Export processing rules as CSV (always uses API 1.4)"""
    # Processing rules are NOT available in API 2.0, so we always use 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('processing_rules', lambda: api.get_processing_rules(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, PROCRULES_COLUMNS)

    return generate_csv(data, f'{rsid}_processing_rules.csv')


@main_bp.route('/marketing-channels')
def marketing_channels():
    """Display marketing channels (uses API 1.4 for full config data)"""
    # Marketing channel config is better exposed in API 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('marketing_channels', lambda: api.get_marketing_channels(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, MKTCHANNELS_COLUMNS)

    return render_listing('Marketing Channels', data, list(MKTCHANNELS_COLUMNS.values()), 'marketing-channels', cache_key='marketing_channels')


@main_bp.route('/marketing-channels/export')
def marketing_channels_export():
    """Export marketing channels as CSV (uses API 1.4)"""
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('marketing_channels', lambda: api.get_marketing_channels(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, MKTCHANNELS_COLUMNS)

    return generate_csv(data, f'{rsid}_marketing_channels.csv')


@main_bp.route('/channel-rules')
def channel_rules():
    """Display marketing channel rules (always uses API 1.4 - not available in 2.0)"""
    # Channel rules are NOT available in API 2.0, so we always use 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('channel_rules', lambda: api.get_marketing_channel_rules(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, MKTRULES_COLUMNS)

    return render_listing(
        'Channel Rules', data, list(MKTRULES_COLUMNS.values()), 'channel-rules',
        monospace_columns=['Query String', 'Hit Attribute', 'Hit Query Param', 'Matches'],
        cache_key='channel_rules'
    )


@main_bp.route('/channel-rules/export')
def channel_rules_export():
    """Export channel rules as CSV (always uses API 1.4)"""
    # Channel rules are NOT available in API 2.0, so we always use 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('channel_rules', lambda: api.get_marketing_channel_rules(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, MKTRULES_COLUMNS)

    return generate_csv(data, f'{rsid}_channel_rules.csv')


# =============================================================================
# Calculated Metrics Routes (API 2.0)
# =============================================================================

@main_bp.route('/calculated-metrics')
def calculated_metrics():
    """Display all calculated metrics for the configured report suite (API 2.0)."""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data(
        'calculated_metrics', lambda: api.get_calculated_metrics(rsid),
        ttl_hours=CONFIG_TTL_HOURS,
    )
    data = transform_data(raw_data, CALC_METRICS_COLUMNS)

    for i, row in enumerate(data):
        row['cm_id'] = raw_data[i]['id']

    return render_listing(
        'Calculated Metrics', data, list(CALC_METRICS_COLUMNS.values()),
        'calculated-metrics',
        cache_key='calculated_metrics',
        column_styles={'Name': 'max-width:320px; white-space:normal; word-break:break-word;'},
        dt_order=[[3, 'desc']],
        column_badges={
            'Type': {
                'decimal':  '<span class="badge bg-info text-dark">0.0</span>',
                'percent':  '<span class="badge bg-success">%</span>',
                'currency': '<span class="badge bg-warning text-dark">$</span>',
                'time':     '<span class="badge bg-secondary">0:00</span>',
            }
        },
    )


@main_bp.route('/calculated-metrics/export')
def calculated_metrics_export():
    """Export calculated metrics as CSV (API 2.0)."""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data(
        'calculated_metrics', lambda: api.get_calculated_metrics(rsid),
        ttl_hours=CONFIG_TTL_HOURS,
    )
    data = transform_data(raw_data, CALC_METRICS_COLUMNS)
    return generate_csv(data, f'{rsid}_calculated_metrics.csv')


@main_bp.route('/calculated-metrics/<cm_id>')
def calculated_metric_detail(cm_id: str):
    """Display detail page for a single calculated metric (API 2.0)."""
    api = get_api_service()
    rsid = get_rsid()

    cm = cache.get_or_set(
        rsid, f'cm_detail_{cm_id}',
        lambda: api.get_calculated_metric(cm_id),
        ttl_hours=CONFIG_TTL_HOURS,
    )

    if not cm:
        abort(404)

    refs = _parse_calc_metric_formula(cm.get('definition') or {})

    trend_data = cache.get_or_set(
        rsid, f'cm_trend_{cm_id}',
        lambda: api.get_metric_trend(rsid, cm_id),
        ttl_hours=1,
    )

    return render_template(
        'calc_metric_detail.html',
        title=cm.get('name', cm_id),
        cm=cm,
        cm_id=cm_id,
        refs=refs,
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='calculated-metrics',
        back_url='/calculated-metrics',
        back_label='Back to Calculated Metrics',
        definition_json=json.dumps(cm.get('definition') or {}, indent=2),
        trend_data=trend_data,
    )


# =============================================================================
# Segments Routes (API 2.0)
# =============================================================================

@main_bp.route('/segments')
def segments():
    """Display segments for the configured report suite (API 2.0)."""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data('segments', lambda: api.get_segments(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, SEGMENTS_COLUMNS)

    # Attach the segment ID to each row so the template can build detail links.
    # segment_id is not in SEGMENTS_COLUMNS so it never renders as a column.
    for i, row in enumerate(data):
        row['segment_id'] = raw_data[i]['id']

    return render_listing(
        'Segments', data, list(SEGMENTS_COLUMNS.values()), 'segments',
        cache_key='segments',
        column_styles={'Name': 'max-width:320px; white-space:normal; word-break:break-word;'},
    )


@main_bp.route('/segments/export')
def segments_export():
    """Export segments as CSV (API 2.0)."""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data('segments', lambda: api.get_segments(rsid), ttl_hours=CONFIG_TTL_HOURS)
    data = transform_data(raw_data, SEGMENTS_COLUMNS)

    return generate_csv(data, f'{rsid}_segments.csv')


@main_bp.route('/segments/<segment_id>')
def segment_detail(segment_id: str):
    """Display detail page for a single segment (API 2.0)."""
    api = get_api_service()
    rsid = get_rsid()

    segment = cache.get_or_set(
        rsid, f'segment_detail_{segment_id}',
        lambda: api.get_segment(segment_id),
        ttl_hours=CONFIG_TTL_HOURS,
    )

    if not segment:
        abort(404)

    # Build a readable summary of what variables/events the segment references.
    schema = (segment.get('compatibility') or {}).get('schema', [])
    referenced = _parse_segment_schema(schema)

    return render_template(
        'segment_detail.html',
        title=segment.get('name', segment_id),
        segment=segment,
        segment_id=segment_id,
        referenced=referenced,
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='segments',
        back_url='/segments',
        back_label='Back to Segments',
        definition_json=json.dumps(segment.get('definition') or {}, indent=2),
    )


REPORT_SUITES_COLUMNS = {
    'rsid':     'Report Suite ID',
    'name':     'Name',
    'type':     'Type',
    'currency': 'Currency',
    'timezone': 'Timezone',
}

@main_bp.route('/report-suites')
def report_suites():
    """Display all report suites accessible to this service account (API 2.0)."""
    api = get_api_service()
    current_rsid = get_rsid()

    raw_data = get_cached_data(
        'report_suites', lambda: api.get_report_suites(), ttl_hours=CONFIG_TTL_HOURS
    )
    data = transform_data(raw_data, REPORT_SUITES_COLUMNS)

    # Find the configured suite's name for the page note
    configured_name = next(
        (row['Name'] for row in data if row.get('Report Suite ID') == current_rsid),
        current_rsid,
    )

    return render_listing(
        'Report Suites',
        data,
        list(REPORT_SUITES_COLUMNS.values()),
        'report-suites',
        cache_key='report_suites',
        monospace_columns=['Report Suite ID'],
        page_note=f'Currently configured report suite: {configured_name} ({current_rsid})',
    )


@main_bp.route('/report-suites/export')
def report_suites_export():
    """Export report suites as CSV (API 2.0)."""
    api = get_api_service()

    raw_data = get_cached_data(
        'report_suites', lambda: api.get_report_suites(), ttl_hours=CONFIG_TTL_HOURS
    )
    data = transform_data(raw_data, REPORT_SUITES_COLUMNS)
    return generate_csv(data, 'report_suites.csv')


@main_bp.route('/cache')
def cache_view():
    """Display cache information"""
    rsid = get_rsid()
    cache_info = get_cache_info()

    return render_template(
        'cache.html',
        title='Cache',
        cache_info=cache_info,
        rsid=rsid,
        active_tab='cache'
    )


@main_bp.route('/cache/clear')
def cache_clear():
    """Clear cache and redirect to cache view"""
    rsid = get_rsid()
    cache.clear(rsid)

    return render_template(
        'cache.html',
        title='Cache',
        cache_info=get_cache_info(),
        rsid=rsid,
        active_tab='cache',
        message='Cache cleared successfully'
    )


@main_bp.route('/cache/refresh/<cache_key>')
def cache_refresh(cache_key):
    """Clear a specific cache key and re-warm it."""
    from app.services.cache_warmer import CONFIG_CACHE_KEYS, warm_cache_key

    if cache_key not in CONFIG_CACHE_KEYS:
        abort(400)

    rsid = get_rsid()
    cache.clear_key(rsid, cache_key)
    warm_cache_key(current_app._get_current_object(), rsid, cache_key)

    return redirect(request.referrer or '/')


# =============================================================================
# Components Fragment API
# =============================================================================

def _find_components(rsid: str, variable_id: str) -> dict:
    """Find segments and calculated metrics whose definitions reference a variable.

    Searches the cached listing data (which includes ``definition`` fields).
    Exact matching uses the quoted form ``'"<variable_id>"'`` to prevent false
    substring matches (e.g. ``prop1`` matching ``prop10``).

    Calculated metrics can reference a prop or eVar **transitively** — the CM
    formula never references the variable directly; instead it references a
    segment (via a ``segment-ref`` node) whose own definition references the
    variable.  A two-pass approach handles both cases:

    1. Find every segment whose definition contains the variable_id.
    2. Find every CM whose definition either:
       (a) directly contains the variable_id (works for events/metrics), or
       (b) references the ID of any segment found in step 1 (works for
           props/evars that are embedded inside segment filters).

    Args:
        rsid:        Report suite ID (used to key the cache lookup).
        variable_id: Fully-qualified variable identifier, e.g. ``variables/prop1``
                     or ``metrics/event3``.

    Returns:
        Dict with ``segments`` and ``calc_metrics`` keys, each a list of
        ``{id, name}`` dicts for matched items.
    """
    segments_raw = cache.get(rsid, 'segments') or []
    calc_metrics_raw = cache.get(rsid, 'calculated_metrics') or []
    needle = f'"{variable_id}"'

    # Pass 1: segments that directly reference this variable
    matching_segments = []
    matched_segment_ids: set[str] = set()
    for seg in segments_raw:
        definition = seg.get('definition')
        if definition and needle in json.dumps(definition):
            matching_segments.append({'id': seg['id'], 'name': seg.get('name', seg['id'])})
            matched_segment_ids.add(seg['id'])

    # Pass 2: calculated metrics that reference the variable directly OR
    # via one of the matched segments (transitive look-through)
    matching_metrics = []
    for cm in calc_metrics_raw:
        definition = cm.get('definition')
        if not definition:
            continue
        definition_str = json.dumps(definition)
        direct = needle in definition_str
        transitive = any(f'"{seg_id}"' in definition_str for seg_id in matched_segment_ids)
        if direct or transitive:
            matching_metrics.append({'id': cm['id'], 'name': cm.get('name', cm['id'])})

    return {'segments': matching_segments, 'calc_metrics': matching_metrics}


@main_bp.route('/api/components/<dimension_type>/<dimension_id>')
def api_components(dimension_type: str, dimension_id: str):
    """Return the "Components" card as an HTML fragment.

    Called asynchronously by detail pages after initial render so that a cold
    segments/calculated-metrics cache doesn't block page load.

    Args:
        dimension_type: ``prop``, ``evar``, ``event``, or ``listvar``
        dimension_id:   Display ID (e.g. ``prop3``, ``evar5``, ``event2``)
                        or listvar number (e.g. ``1``).
    """
    rsid = get_rsid()

    variable_id_map = {
        'prop':    f'variables/{dimension_id}',
        'evar':    f'variables/{dimension_id}',
        'event':   f'metrics/{dimension_id}',
        'listvar': f'variables/listvar{dimension_id}',
    }
    variable_id = variable_id_map.get(dimension_type, f'variables/{dimension_id}')

    components = _find_components(rsid, variable_id)
    segments_cached = cache.get(rsid, 'segments') is not None
    calc_metrics_cached = cache.get(rsid, 'calculated_metrics') is not None

    return render_template(
        '_fragment_components.html',
        components=components,
        segments_cached=segments_cached,
        calc_metrics_cached=calc_metrics_cached,
    )


# =============================================================================
# Processing Rules Fragment API
# =============================================================================

@main_bp.route('/api/related-rules/<dimension_type>/<dimension_id>')
def api_related_rules(dimension_type: str, dimension_id: str):
    """Return the "Related Processing Rules" card as an HTML fragment.

    Called asynchronously by detail pages after initial render so that a cold
    or unavailable processing-rules cache doesn't block page load.

    Args:
        dimension_type: 'prop', 'evar', 'event', or 'listvar'
        dimension_id:   The dimension's display ID (e.g. 'prop3', 'evar5',
                        'event2') or listvar number (e.g. '1').
    """
    rsid = get_rsid()
    _cached_rules_raw = cache.get(rsid, 'processing_rules')
    processing_rules_cached = _cached_rules_raw is not None

    if dimension_type == 'listvar':
        # Search for both 'list1' (Adobe internal) and 'listvar1' (API 2.0 ID)
        related_rules = find_related_processing_rules(
            _cached_rules_raw or [],
            f'list{dimension_id}',
            f'listvar{dimension_id}',
        )
    else:
        related_rules = find_related_processing_rules(
            _cached_rules_raw or [], dimension_id
        )

    formatted_rules = [
        {**rule, 'rules': format_conditions(rule.get('rules', ''))}
        for rule in related_rules
    ]
    return render_template(
        '_fragment_related_rules.html',
        related_rules=formatted_rules,
        processing_rules_cached=processing_rules_cached,
    )


# =============================================================================
# Notes API Routes
# =============================================================================

@main_bp.route('/api/notes/<dimension_type>/<dimension_id>', methods=['GET'])
def get_note(dimension_type: str, dimension_id: str):
    """
    Get a note for a specific dimension.
    
    Args:
        dimension_type: Type of dimension (prop, evar, event, listvar)
        dimension_id: The dimension identifier (e.g., 'prop1', 'evar5', 'event10')
    
    Returns:
        JSON with all note fields
    """
    rsid = get_rsid()
    note = notes_service.get(rsid, dimension_type, dimension_id)
    return jsonify(note)


@main_bp.route('/api/notes/<dimension_type>/<dimension_id>', methods=['POST'])
def save_note(dimension_type: str, dimension_id: str):
    """
    Save a note for a specific dimension.
    
    Args:
        dimension_type: Type of dimension (prop, evar, event, listvar)
        dimension_id: The dimension identifier (e.g., 'prop1', 'evar5', 'event10')
    
    Request body:
        JSON with note fields
    
    Returns:
        JSON with saved note data including updated_at
    """
    rsid = get_rsid()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    note = notes_service.set(rsid, dimension_type, dimension_id, data)
    return jsonify(note)


@main_bp.route('/api/notes/<dimension_type>/<dimension_id>', methods=['DELETE'])
def delete_note(dimension_type: str, dimension_id: str):
    """
    Delete a note for a specific dimension.
    
    Args:
        dimension_type: Type of dimension (prop, evar, event, listvar)
        dimension_id: The dimension identifier (e.g., 'prop1', 'evar5', 'event10')
    
    Returns:
        JSON with success status
    """
    rsid = get_rsid()
    deleted = notes_service.delete(rsid, dimension_type, dimension_id)
    return jsonify({'deleted': deleted})


@main_bp.route('/api/notes/options/<dimension_type>')
def get_dimension_options(dimension_type: str):
    """
    Get list of dimensions for Web/App Equivalent dropdowns.
    
    Args:
        dimension_type: Type of dimension (prop, evar, event, listvar)
    
    Returns:
        JSON array of {id, name} objects for the specified dimension type
    """
    rsid = get_rsid()
    api = get_api_service()
    
    # Get cached dimensions (used for props, evars, listvars)
    cached_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid), ttl_hours=CONFIG_TTL_HOURS)
    
    options = [
        {"id": "", "name": "Not Set"},
        {"id": "none", "name": "None"}
    ]
    
    if dimension_type == 'prop' and cached_dimensions:
        for dim in cached_dimensions:
            dim_id = dim.get('id', '')
            # Match variables/prop1, variables/prop2, etc. (exclude classifications with dots)
            if dim_id.startswith('variables/prop') and '.' not in dim_id.replace('variables/', ''):
                short_id = dim_id.replace('variables/', '')
                name = dim.get('name') or dim.get('title') or ''
                if name and name != short_id:  # Only include named dimensions
                    options.append({"id": short_id, "name": f"{short_id}: {name}"})
        # Sort by prop number
        options[2:] = sorted(options[2:], key=lambda x: safe_extract_dimension_number(x['id'], 'prop'))
    
    elif dimension_type == 'evar' and cached_dimensions:
        for dim in cached_dimensions:
            dim_id = dim.get('id', '')
            # Match variables/evar1, variables/evar2, etc. (exclude classifications with dots)
            if dim_id.startswith('variables/evar') and '.' not in dim_id.replace('variables/', ''):
                short_id = dim_id.replace('variables/', '')
                name = dim.get('name') or dim.get('title') or ''
                if name and name != short_id:  # Only include named dimensions
                    options.append({"id": short_id, "name": f"{short_id}: {name}"})
        # Sort by evar number
        options[2:] = sorted(options[2:], key=lambda x: safe_extract_dimension_number(x['id'], 'evar'))
    
    elif dimension_type == 'event':
        # Events are fetched via get_success_events, cached under 'events' key
        cached_events = get_cached_data('events', lambda: api.get_success_events(rsid), ttl_hours=CONFIG_TTL_HOURS)
        if cached_events:
            for event in cached_events:
                event_id = event.get('id', '')
                name = event.get('name') or ''
                if name and name != event_id:  # Only include named events
                    options.append({"id": event_id, "name": f"{event_id}: {name}"})
            # Sort by event number
            options[2:] = sorted(options[2:], key=lambda x: safe_extract_dimension_number(x['id'], 'event'))
    
    elif dimension_type == 'listvar' and cached_dimensions:
        for dim in cached_dimensions:
            dim_id = dim.get('id', '')
            if dim_id.startswith('variables/listvar'):
                short_id = dim_id.replace('variables/', '')
                name = dim.get('name') or dim.get('title') or ''
                if name and name != short_id:
                    options.append({"id": short_id, "name": f"{short_id}: {name}"})
        # Sort by listvar number
        options[2:] = sorted(options[2:], key=lambda x: safe_extract_dimension_number(x['id'], 'listvar'))
    
    return jsonify(options)


