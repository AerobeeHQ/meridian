"""
Main routes for the Codex application
"""
import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, render_template, current_app, Response

from app.services.adobe_analytics import AdobeAnalyticsService
from app.services.adobe_analytics_v2 import AdobeAnalyticsV2Service
from app.services.adobe_auth import OAuth2Auth
from app.services.cache import CacheService


main_bp = Blueprint('main', __name__)

# Initialize cache service
cache = CacheService()


@main_bp.app_context_processor
def inject_git_info():
    """Inject git info into all templates"""
    return {
        'git_branch': current_app.config.get('GIT_BRANCH'),
        'git_commit': current_app.config.get('GIT_COMMIT')
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
            secret=current_app.config['AW_SECRET']
        )
    return app.codex_api_service_v14


def get_rsid() -> str:
    """Get configured report suite ID"""
    return current_app.config['AW_REPORTSUITE_ID']


def get_cached_data(key: str, fetch_func):
    """Get data from cache or fetch from API"""
    rsid = get_rsid()
    return cache.get_or_set(rsid, key, fetch_func)


def get_cache_info() -> dict:
    """Get cache information for footer"""
    rsid = get_rsid()
    return cache.get_info(rsid)


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


@main_bp.route('/')
@main_bp.route('/props')
def props():
    """Display traffic variables (props)"""
    api = get_api_service()
    rsid = get_rsid()

    # Cache raw dimensions for reuse by detail pages (Quick Win #1)
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid))
    
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

    return render_template(
        'table.html',
        title='Props',
        app_title=current_app.config['APP_TITLE'],
        data=data,
        columns=list(PROPS_COLUMNS.values()),
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='props',
        monospace_columns=[]
    )


@main_bp.route('/props/export')
def props_export():
    """Export props as CSV"""
    api = get_api_service()
    rsid = get_rsid()

    # Use cached dimensions
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid))
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
        app_title=current_app.config['APP_TITLE'],
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
        back_label='Back to Props Listing'
    )


@main_bp.route('/evars')
def evars():
    """Display conversion variables (eVars)"""
    api = get_api_service()
    rsid = get_rsid()

    # Cache raw dimensions for reuse by detail pages (Quick Win #1)
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid))
    
    # Filter eVars from dimensions and transform
    # Exclude classifications (IDs containing a dot after the evar number, e.g., evar101.catalogue-name)
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

    return render_template(
        'table.html',
        title='eVars',
        app_title=current_app.config['APP_TITLE'],
        data=data,
        columns=list(EVARS_COLUMNS.values()),
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='evars',
        monospace_columns=[]
    )


@main_bp.route('/evars/export')
def evars_export():
    """Export eVars as CSV"""
    api = get_api_service()
    rsid = get_rsid()

    # Use cached dimensions
    raw_dimensions = get_cached_data('dimensions', lambda: api.get_dimensions(rsid))
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

    def fetch_top_items():
        return api.get_top_items(rsid, dimension_id, metric="occurrences", limit=10, days=30)

    def fetch_trend():
        return api.get_dimension_trend(rsid, dimension_id, metric="occurrences", days=30)

    # Quick Win #2: Check cache first, then parallelize needed API calls
    dimension = cache.get(rsid, f'evar_detail_{display_id}')
    top_items = cache.get(rsid, f'evar_top_{display_id}')
    trend_data = cache.get(rsid, f'evar_trend_{display_id}')

    tasks = {}
    if dimension is None:
        tasks['dimension'] = fetch_dimension
    if top_items is None:
        tasks['top_items'] = fetch_top_items
    if trend_data is None:
        tasks['trend_data'] = fetch_trend

    if tasks:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(func): key for key, func in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                value = future.result()
                if key == 'dimension':
                    cache.set(rsid, f'evar_detail_{display_id}', value)
                    dimension = value
                elif key == 'top_items':
                    cache.set(rsid, f'evar_top_{display_id}', value)
                    top_items = value
                elif key == 'trend_data':
                    cache.set(rsid, f'evar_trend_{display_id}', value)
                    trend_data = value

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
        app_title=current_app.config['APP_TITLE'],
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
        back_label='Back to eVars Listing'
    )


@main_bp.route('/events')
def events():
    """Display success events"""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data('events', lambda: api.get_success_events(rsid))
    data = transform_data(raw_data, EVENTS_COLUMNS)

    return render_template(
        'table.html',
        title='Events',
        app_title=current_app.config['APP_TITLE'],
        data=data,
        columns=list(EVENTS_COLUMNS.values()),
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='events',
        monospace_columns=[]
    )


@main_bp.route('/events/export')
def events_export():
    """Export events as CSV"""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data('events', lambda: api.get_success_events(rsid))
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
        app_title=current_app.config['APP_TITLE'],
        metric=metric,
        event_id=display_id,
        trend_data=trend_data,
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='events',
        back_url='/events',
        back_label='Back to Events Listing'
    )


@main_bp.route('/listvars')
def listvars():
    """Display list variables (uses API 1.4 for full config data)"""
    # List variable config is better exposed in API 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('listvars', lambda: api.get_list_variables(rsid))
    data = transform_data(raw_data, LISTVARS_COLUMNS)

    return render_template(
        'table.html',
        title='ListVars',
        app_title=current_app.config['APP_TITLE'],
        data=data,
        columns=list(LISTVARS_COLUMNS.values()),
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='listvars',
        monospace_columns=[]
    )


@main_bp.route('/listvars/export')
def listvars_export():
    """Export list variables as CSV (uses API 1.4)"""
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('listvars', lambda: api.get_list_variables(rsid))
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
    import re
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
        app_title=current_app.config['APP_TITLE'],
        listvar=listvar or {},
        listvar_name=listvar_name,
        listvar_num=listvar_num,
        top_items=top_items or [],
        trend_data=trend_data or {},
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='listvars',
        back_url='/listvars',
        back_label='Back to ListVars Listing'
    )


@main_bp.route('/processing-rules')
def processing_rules():
    """Display processing rules (always uses API 1.4 - not available in 2.0)"""
    # Processing rules are NOT available in API 2.0, so we always use 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('processing_rules', lambda: api.get_processing_rules(rsid))
    data = transform_data(raw_data, PROCRULES_COLUMNS)

    return render_template(
        'table.html',
        title='Proc Rules',
        app_title=current_app.config['APP_TITLE'],
        data=data,
        columns=list(PROCRULES_COLUMNS.values()),
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='processing-rules',
        monospace_columns=['Actions', 'Conditions']
    )


@main_bp.route('/processing-rules/export')
def processing_rules_export():
    """Export processing rules as CSV (always uses API 1.4)"""
    # Processing rules are NOT available in API 2.0, so we always use 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('processing_rules', lambda: api.get_processing_rules(rsid))
    data = transform_data(raw_data, PROCRULES_COLUMNS)

    return generate_csv(data, f'{rsid}_processing_rules.csv')


@main_bp.route('/marketing-channels')
def marketing_channels():
    """Display marketing channels (uses API 1.4 for full config data)"""
    # Marketing channel config is better exposed in API 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('marketing_channels', lambda: api.get_marketing_channels(rsid))
    data = transform_data(raw_data, MKTCHANNELS_COLUMNS)

    return render_template(
        'table.html',
        title='Marketing Channels',
        app_title=current_app.config['APP_TITLE'],
        data=data,
        columns=list(MKTCHANNELS_COLUMNS.values()),
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='marketing-channels',
        monospace_columns=[]
    )


@main_bp.route('/marketing-channels/export')
def marketing_channels_export():
    """Export marketing channels as CSV (uses API 1.4)"""
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('marketing_channels', lambda: api.get_marketing_channels(rsid))
    data = transform_data(raw_data, MKTCHANNELS_COLUMNS)

    return generate_csv(data, f'{rsid}_marketing_channels.csv')


@main_bp.route('/channel-rules')
def channel_rules():
    """Display marketing channel rules (always uses API 1.4 - not available in 2.0)"""
    # Channel rules are NOT available in API 2.0, so we always use 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('channel_rules', lambda: api.get_marketing_channel_rules(rsid))
    data = transform_data(raw_data, MKTRULES_COLUMNS)

    return render_template(
        'table.html',
        title='Channel Rules',
        app_title=current_app.config['APP_TITLE'],
        data=data,
        columns=list(MKTRULES_COLUMNS.values()),
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='channel-rules',
        monospace_columns=['Query String', 'Hit Attribute', 'Hit Query Param', 'Matches']
    )


@main_bp.route('/channel-rules/export')
def channel_rules_export():
    """Export channel rules as CSV (always uses API 1.4)"""
    # Channel rules are NOT available in API 2.0, so we always use 1.4
    api = get_api_service_v14()
    rsid = get_rsid()

    raw_data = get_cached_data('channel_rules', lambda: api.get_marketing_channel_rules(rsid))
    data = transform_data(raw_data, MKTRULES_COLUMNS)

    return generate_csv(data, f'{rsid}_channel_rules.csv')


@main_bp.route('/report-suites')
def report_suites():
    """Display report suites"""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data('report_suites', lambda: api.get_report_suites())

    # Report suites have variable structure, just use as-is
    if raw_data:
        columns = list(raw_data[0].keys())
    else:
        columns = []

    return render_template(
        'table.html',
        title='Report Suites',
        app_title=current_app.config['APP_TITLE'],
        data=raw_data,
        columns=columns,
        rsid=rsid,
        cache_info=get_cache_info(),
        active_tab='report-suites',
        monospace_columns=[]
    )


@main_bp.route('/report-suites/export')
def report_suites_export():
    """Export report suites as CSV"""
    api = get_api_service()
    rsid = get_rsid()

    raw_data = get_cached_data('report_suites', lambda: api.get_report_suites())

    return generate_csv(raw_data, 'report_suites.csv')


@main_bp.route('/cache')
def cache_view():
    """Display cache information"""
    rsid = get_rsid()
    cache_info = get_cache_info()

    return render_template(
        'cache.html',
        title='Cache',
        app_title=current_app.config['APP_TITLE'],
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
        app_title=current_app.config['APP_TITLE'],
        cache_info=get_cache_info(),
        rsid=rsid,
        active_tab='cache',
        message='Cache cleared successfully'
    )

