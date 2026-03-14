# 012 - Success Events and ListVars Detail Views

## Date
March 14, 2026

## Summary
Extended the enhancements made for Props and eVars listing/detail pages to the Success Events and ListVars views. This includes clickable IDs in the listing tables and dedicated detail pages showing configuration, 30-day trend charts, top values (for ListVars), and summary statistics.

## Changes Made

### 1. Clickable Event and ListVar IDs (table.html)
Updated the table template to make Event and ListVar IDs clickable links:
```html
{% elif col == 'Event' and row[col] %}
    <a href="/events/{{ row[col] }}">{{ row[col] }}</a>
{% elif col == 'ListVar' and row[col] %}
    <a href="/listvars/{{ row[col] }}">{{ row[col] }}</a>
```

### 2. Event Detail Route (main.py)
Added new route `/events/<event_id>` with:
- Parallel API calls using ThreadPoolExecutor for metric details and trend data
- Caching of event details and trend data
- Renders the new `event_detail.html` template

### 3. Event Detail Template (event_detail.html)
Created new template showing:
- **Event Configuration card**: Event ID, Label, Type, Status, Polarity, Precision, Serialization, Description
- **30-Day Summary card**: Total, Daily Average, Median, Peak, and Lowest values
- **Trend Chart**: Line chart showing daily event counts (Chart.js)
- **Summary Statistics cards**: Average, Median, Peak, Min

### 4. ListVar Detail Route (main.py)
Added new route `/listvars/<listvar_name>` with:
- Hybrid API approach: config from API 1.4, trend/top data from API 2.0
- Parallel API calls for config, top items, and trend data
- Maps ListVar name (e.g., "List Var 1") to dimension ID (e.g., "variables/listvar1")

### 5. ListVar Detail Template (listvar_detail.html)
Created new template showing:
- **ListVar Configuration card**: Name, ID, Enabled status, Allocation, Expiration, Delimiter, Max Values, Description
- **Top 10 Values card**: Most common values with counts and percentages
- **Trend Chart**: Line chart showing daily occurrences (Chart.js)
- **Summary Statistics cards**: Average, Median, Peak, Min

### 6. API Service Methods (adobe_analytics_v2.py)
Added two new methods:
- `get_metric(rsid, metric_id)`: Fetches details for a single metric/event
- `get_event_trend(rsid, event_id, days)`: Gets daily trend data for an event

## Files Modified
- `app/templates/table.html` - Added Event and ListVar ID link handling
- `app/routes/main.py` - Added `event_detail()` and `listvar_detail()` routes
- `app/services/adobe_analytics_v2.py` - Added `get_metric()` and `get_event_trend()` methods

## Files Created
- `app/templates/event_detail.html` - Event detail page template
- `app/templates/listvar_detail.html` - ListVar detail page template

## Technical Notes
- Events use "metrics/" prefix (e.g., `metrics/event1`) vs dimensions using "variables/" prefix
- ListVars use API 1.4 for configuration data but API 2.0 for reporting (top items, trends)
- ListVar names like "List Var 1" map to dimension IDs like "variables/listvar1"
- All detail pages use consistent Chart.js configuration for visual consistency
