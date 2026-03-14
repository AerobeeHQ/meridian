# 012 - Success Events Listing and Detail Views

## Date
March 14, 2026

## Summary
Extended the enhancements made for Props and eVars listing/detail pages to the Success Events views. This includes clickable Event IDs in the listing table and a dedicated detail page showing event configuration, 30-day trend chart, and summary statistics.

## Changes Made

### 1. Clickable Event IDs (table.html)
Updated the table template to make Event IDs clickable links that navigate to the event detail page:
```html
{% elif col == 'Event' and row[col] %}
    <a href="/events/{{ row[col] }}">{{ row[col] }}</a>
```

### 2. Event Detail Route (main.py)
Added new route `/events/<event_id>` with:
- Parallel API calls using ThreadPoolExecutor for metric details and trend data
- Caching of event details and trend data
- Renders the new `event_detail.html` template

### 3. Event Detail Template (event_detail.html)
Created new template based on the dimension detail template, adapted for events:
- **Event Configuration card**: Displays Event ID, Label, Type, Status, Polarity, Precision, Serialization, and Description
- **30-Day Summary card**: Shows Total, Daily Average, Daily Median, Peak Day, and Lowest Day statistics
- **Trend Chart**: Line chart showing daily event counts over the last 30 days (using Chart.js)
- **Summary Statistics cards**: Four cards showing Average, Median, Peak, and Min values

### 4. API Service Methods (adobe_analytics_v2.py)
Added two new methods:
- `get_metric(rsid, metric_id)`: Fetches details for a single metric/event from the cached metrics list
- `get_event_trend(rsid, event_id, days)`: Gets daily trend data for an event over the specified period, returning dates, values, and calculated statistics (avg, median, max, min)

## Files Modified
- `app/templates/table.html` - Added Event ID link handling
- `app/routes/main.py` - Added `event_detail()` route
- `app/services/adobe_analytics_v2.py` - Added `get_metric()` and `get_event_trend()` methods

## Files Created
- `app/templates/event_detail.html` - Event detail page template

## Technical Notes
- Events use "metrics/" prefix (e.g., `metrics/event1`) vs dimensions using "variables/" prefix
- Event trends query the event as the metric with `daterangeday` as the dimension
- The detail page uses the same Chart.js configuration as the dimension detail pages for visual consistency

