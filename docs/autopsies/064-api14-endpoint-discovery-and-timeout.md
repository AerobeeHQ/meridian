# 064 — API 1.4 Endpoint Discovery and Timeout Fix

**Date:** 2026-05-22
**Branch:** `fix/api14-endpoint-discovery-and-timeout`
**Status:** Complete

---

## Problem

The Processing Rules, Marketing Channels, and Channel Rules pages — all of which rely exclusively on Adobe Analytics API 1.4 — were consistently failing with an "API Unavailable" error on the Coles deployment.

Expanding the "Technical details" disclosure on the error page revealed:

```
Error type:  ReadTimeout
Message:     HTTPSConnectionPool(host='api3.omniture.com', port=443):
             Read timed out. (read timeout=2)
```

Two root causes were identified by comparing the Codex implementation against the working RShiny app (which uses the RSiteCatalyst R library):

### Root cause 1 — Read timeout too short

The configured `API_V14_TIMEOUT` value of `2` seconds was used as **both** the connect timeout and the read timeout for every request. Adobe's API servers accept the TCP connection quickly but can take several seconds to process and respond to authenticated requests. A 2-second read timeout was consistently too short, causing all four `omniture.com` fallback endpoints to be rejected before any response arrived.

The RSiteCatalyst library has no hard read timeout by default — it waits as long as needed once the connection is established.

### Root cause 2 — No endpoint discovery

Codex used a hardcoded round-robin of four generic endpoints (`api.omniture.com`, `api2.omniture.com`, `api3.omniture.com`, `api4.omniture.com`). Adobe assigns each company to a specific regional API host, and only that host handles the company's authenticated requests efficiently.

RSiteCatalyst calls `Company.GetEndpoint` (an unauthenticated public lookup) at startup to resolve the correct host for the company, then uses that host exclusively. Codex was skipping this step, meaning every request had to cycle through incorrect hosts before (sometimes) landing on the right one.

---

## Investigation

### How RSiteCatalyst determines the endpoint

Reading the compiled RSiteCatalyst source via `Rscript -e "library(RSiteCatalyst); print(RSiteCatalyst:::GetEndpoint)"` revealed:

```r
function(company) {
    endpoint <- content(
        POST("https://api.omniture.com/admin/1.4/rest/?method=Company.GetEndpoint",
             body = sprintf("{\"company\": \"%s\"}", company)),
        "text", encoding = "UTF-8"
    )
    endpoint <- gsub("\\", "", gsub("\"", "", endpoint, fixed=TRUE), fixed=TRUE)
    return(endpoint)
}
```

The call is made without any WSSE authentication. Adobe returns a plain JSON-encoded string containing the correct endpoint URL for the company.

### Why the WSSE format was not the cause

An alternative hypothesis was that the Codex WSSE implementation differed from RSiteCatalyst's. Inspection of `BuildHeader` in RSiteCatalyst confirmed a different algorithm (Unix-timestamp nonce, hex SHA1 base64-encoded as ASCII). However, the error in production was a `ReadTimeout`, not an `HTTPError` (401). A WSSE mismatch would produce an HTTP authentication failure, not a timeout. The WSSE implementation was ruled out as a contributing factor.

---

## Solution

### 1. Split connect timeout from read timeout (`adobe_analytics.py`)

Added `_MIN_READ_TIMEOUT = 30.0` class constant and a `_compute_timeout()` helper that returns a `(connect, read)` tuple:

```python
def _compute_timeout(self):
    if isinstance(self.request_timeout, tuple):
        return self.request_timeout
    read = max(self.request_timeout, self._MIN_READ_TIMEOUT)
    return (self.request_timeout, read)
```

The **connect timeout** (short, from config) still determines how quickly the service fails over to the next endpoint if a server does not accept connections. The **read timeout** is at least 30 seconds regardless of the configured value, giving the API time to respond once connected.

Both `_make_request()` and `_fetch_with_manual_decoding()` now use `_compute_timeout()`.

### 2. Implement `Company.GetEndpoint` discovery (`adobe_analytics.py`)

Added `discover_endpoint()` — a public method that resolves and caches the correct API host for the service's company:

```python
def discover_endpoint(self) -> None:
    company = self.username.split(':', 1)[1]
    response = requests.post(
        f"{self.API_ENDPOINTS[0]}?method=Company.GetEndpoint",
        json={"company": company},
        timeout=10.0,
    )
    endpoint = response.json()
    self._discovered_endpoint = endpoint  # e.g. "https://api3.omniture.com/..."
```

Failures are caught and logged; the service silently falls back to the default rotation if discovery does not succeed.

`_make_request()` now tries `_discovered_endpoint` first (if set) before falling back to the rotation list, avoiding unnecessary attempts against incorrect hosts.

### 3. Call discovery at startup (`app/__init__.py`)

```python
api_v14 = AdobeAnalyticsService(...)
api_v14.discover_endpoint()   # resolve correct endpoint once at startup
```

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_analytics.py` | Added `_MIN_READ_TIMEOUT`; added `discover_endpoint()`; added `_compute_timeout()`; updated `_make_request()` and `_fetch_with_manual_decoding()` |
| `app/__init__.py` | Call `api_v14.discover_endpoint()` after service instantiation |
| `tests/test_adobe_analytics.py` | Added `TestEndpointDiscovery` (6 tests), `TestComputeTimeout` (4 tests), and two new `TestEndpointRotation` cases |
| `docs/autopsies/064-api14-endpoint-discovery-and-timeout.md` | This document |

---

## Tests

Full suite: **166 tests, all passing** (up from 129 before this change — the increase includes the 12 new tests added here plus tests added in earlier sessions).

New test classes:

| Class | Tests | What is covered |
|-------|-------|-----------------|
| `TestEndpointDiscovery` | 6 | Successful discovery; trailing-slash normalisation; no-op without colon in username; silent failure on `ConnectionError`; silent failure on `Timeout`; ignores non-HTTP response |
| `TestComputeTimeout` | 4 | Float timeout produces tuple; read timeout floored at `_MIN_READ_TIMEOUT`; large request timeout used as-is; tuple passed through unchanged |
| `TestEndpointRotation` (added) | 2 | Discovered endpoint is tried first; fallback to rotation when discovered endpoint fails |

---

## Notes

- `API_V14_TIMEOUT` in client config now controls only the **connect** timeout. Existing configs with low values (e.g. `2`) continue to fail fast on unreachable endpoints while waiting properly for responses from reachable ones. No config changes are required.
- The `discover_endpoint()` call adds one unauthenticated HTTP request per client at app startup. The discovery timeout is hardcoded at 10 seconds and is independent of `API_V14_TIMEOUT`.
- If discovery fails (e.g. `api.omniture.com` unreachable at startup), the service falls back to the existing rotation behaviour. The fix degrades gracefully.
