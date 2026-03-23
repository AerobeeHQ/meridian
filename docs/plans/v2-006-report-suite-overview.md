# Plan: Report Suite Summary Overview Page

**Roadmap item:** Add a report suite summary overview page so the user can get a quick snapshot of the state of the Report Suite.

**Complexity: Low–Medium**

---

## Overview

A new `/overview` (or `/`) landing page that aggregates already-cached data into a dashboard-style snapshot. Most of the data is already fetched and cached by existing routes — this page just needs to read and summarise it.

---

## What to Show

### Implementation Health Stats

| Metric | Source |
|--------|--------|
| Total eVars configured | `dimensions` cache (filter `variables/evar*`, count enabled) |
| Total eVars available | Total eVar slots (250) |
| Total Props configured | `dimensions` cache (filter `variables/prop*`, count enabled) |
| Total Success Events configured | `events` cache (count enabled) |
| Total ListVars configured | `listvars` cache |
| Total Processing Rules | `processing_rules` cache |
| Total Marketing Channels | `marketing_channels` cache |

### Recently Updated Dimensions

If notes files exist (`notes/` directory), list dimensions with the most recent `updated_at` timestamp — gives a sense of active documentation work.

### Cache Status

A mini version of the `/cache` page — last refreshed, age, whether any caches are stale.

---

## Implementation Plan

### Step 1 — New route `/overview`

Add a route in `main.py`:

1. Load all cached data using `cache.get()` (not `get_or_set` — don't trigger fetches on the overview page; show what's available).
2. Compute summary stats from the cached data.
3. Render a new template.

```python
@app.route('/overview')
def overview():
    rsid = app.config['AW_REPORTSUITE_ID']
    dimensions = cache.get(rsid, 'dimensions') or []
    events = cache.get(rsid, 'events') or []
    processing_rules = cache.get(rsid, 'processing_rules') or []
    # ... etc

    stats = {
        'evars': {
            'total': count_by_prefix(dimensions, 'variables/evar'),
            'enabled': count_enabled_by_prefix(dimensions, 'variables/evar'),
        },
        'props': { ... },
        'events': { ... },
        # ...
    }
    return render_template('overview.html', stats=stats, rsid=rsid, ...)
```

### Step 2 — Make `/` redirect to `/overview`

Currently `/` redirects to `/props`. Change to redirect to `/overview` instead, making it the natural landing page.

### Step 3 — New template `overview.html`

Layout:

```
[ Page Title: Report Suite Overview ]
[ Subtitle: rsid | Last refreshed: X mins ago ]

[ eVars ]   [ Props ]   [ Events ]   [ ListVars ]
[ 87/250 ]  [ 42/75 ]   [ 63/1000 ] [ 3/4 ]
configured  configured  configured   configured

[ Processing Rules: 24 ]   [ Marketing Channels: 8 ]

[ Recent Documentation Activity ]
  - eVar5 updated 2h ago by ...
  - prop12 updated 1d ago by ...

[ Cache Status ]
  dimensions: fresh (2h ago)
  events: stale
  ...
  [ Refresh All ]
```

Use Bootstrap cards or a simple grid. Colour-code utilisation bars (e.g. green < 50%, yellow 50–80%, red > 80%).

### Step 4 — Navigation

Add "Overview" as the first item in the nav bar in `base.html`.

---

## Files to Create / Change

| File | Change |
|------|--------|
| `app/routes/main.py` | Add `/overview` route; change `/` redirect |
| `app/templates/overview.html` | New: summary dashboard template |
| `app/templates/base.html` | Add Overview link to nav |

---

## Risks & Notes

- **Cold cache:** If caches haven't been populated yet, stats will show zeros. Show a friendly prompt ("Run a cache refresh to populate overview data") rather than confusing empty state.
- **Low risk, high value:** This is the lowest-risk item in the v2 roadmap. All data already exists in the cache — no new API calls or auth changes needed.
- **Good first feature:** Recommended as the first v2 feature to ship, since it only adds a new page without touching existing functionality.
