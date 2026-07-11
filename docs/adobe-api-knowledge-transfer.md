# Adobe API Knowledge Transfer

This document captures non-obvious behaviors, patterns, and gotchas discovered during
Meridian development. Copy the relevant sections into a new project's AGENTS.md.

---

## Authentication

### OAuth2 Server-to-Server (Analytics 2.0 + Reactor)

- Token endpoint: `https://ims-na1.adobelogin.com/ims/token/v3`
- Grant type: `client_credentials`
- Tokens expire in ~24 hours (`expires_in: 86399`). Cache in memory with a 5-minute
  refresh buffer — preemptively refresh when `now + 5min >= expiry`.
- Required headers for every API 2.0 / Reactor request:
  ```
  Authorization: Bearer {access_token}
  x-api-key: {client_id}
  x-gw-ims-org-id: {org_id}   # format: XXXXX@AdobeOrg
  ```
- Same credentials can serve both Analytics 2.0 and Reactor, but may need different
  scopes. Analytics minimum: `openid,AdobeID,additional_info.projectedProductContext`.
  Reactor also needs: `read_organizations,additional_info.roles`.

### WSSE (Analytics 1.4 legacy)

- Header: `X-WSSE: UsernameToken Username="username:company", PasswordDigest="...", Nonce="...", Created="..."`
- `PasswordDigest = Base64(SHA1(Nonce + Created + Secret))` where Nonce is 16 random bytes base64-encoded.
- Generate a **fresh header per request** — the `Created` timestamp must be current.

---

## Analytics API 2.0

### Discovery (required before any other call)

- `GET https://analytics.adobe.io/discovery/me` returns the `globalCompanyId` needed
  in all API paths (`/api/{globalCompanyId}/...`).
- `globalCompanyId` is NOT the same as the IMS Org ID. Don't confuse them.
- Cache this in memory — one call per service lifetime is enough.
- If the configured org ID isn't found in the discovery response, fall back to
  `imsOrgs[0].companies[0]` with a warning log.

### Dimensions & Metrics

- Dimension IDs use prefix format: `variables/prop1`, `variables/evar1`.
- Metric IDs use prefix format: `metrics/event1`.
- Fetch all dimensions/metrics and filter locally — more reliable than the
  single-item endpoint.
- To sort, extract the trailing number with regex (e.g. `evar12` → `12`).

### eVar expiration/allocation metadata

- API 2.0 does **not** expose eVar expiration or allocation as structured fields.
  They are embedded in the description string:
  `"Some description. Expiration: Purchase. Allocation: Merchandising (Last)"`
- Parse with case-insensitive regex. Map to canonical labels
  (hit/visit/day/week/month/quarter/year/purchase_event/never/custom).
- Custom days pattern: `"30 Days"` → `expiration_type=custom, expiration_custom_days=30`.

### Reporting endpoint

- Metric values in rows can be strings (`"N/A"`) when data is unavailable — coerce
  to float, treating invalid values as 0.
- Date dimension returns human-readable strings (`"Jan 1, 2024"`), not ISO dates.

### Segments & Calculated Metrics

- `owner` field is an object with `name` or `login` — try `name` first.
- `tags` is an array of objects; extract the `name` field from each.
- For calculated metrics, pass `includeType=all` to include company-level metrics
  not bound to a specific RSID.

---

## Analytics API 1.4

### When you still need it

API 2.0 does NOT expose everything. Keep 1.4 credentials for:
- Processing rules (`ReportSuite.ViewProcessingRules` — note: `View`, not `Get`)
- Marketing channels and channel rules
- List variables

### Endpoint redundancy

Four load-balanced endpoints: `api.omniture.com`, `api2`, `api3`, `api4`.
On timeout or connection error, rotate to the next endpoint (round-robin).
Remember the working endpoint for subsequent calls.

### Request format

```
POST {endpoint}?method={MethodName}
Headers: X-WSSE, Content-Type: application/json
Body: JSON with method parameters
```

### Response wrapping

Almost all methods return an **array** even for single-suite requests:
```
GetProps  → result[0]["props"]
GetEvars  → result[0]["evars"]
GetEvents → result[0]["events"]
```
Always check `len(result) > 0` before indexing.

### Compression

Responses may be gzip/deflate compressed with broken headers.
If `ContentDecodingError`, retry with `Accept-Encoding: identity` and decompress manually
(try gzip → zlib → plain text). Gracefully return empty dict on JSON decode failure.

### Timeouts

Use `(connect_timeout, read_timeout)` tuple. 5 seconds is reasonable for cross-Pacific.

---

## Reactor (Experience Platform Tags / Launch) API

### Base URL & content type

- Base URL: `https://reactor.adobe.io`
- Accept: `application/vnd.api+json;revision=1`
- Content-Type for writes: `application/vnd.api+json`

### /search endpoint

Use `POST /search` (not GET — it's a POST despite being read-only):
```json
{
  "data": {
    "from": 0, "size": 100,
    "query": {
      "attributes.*": {"value": "eVar1"},
      "relationships.property.data.id": {"value": "PR..."},
      "attributes.deleted_at": {"exists": false},
      "attributes.revision_number": {"value": 0}
    },
    "sort": [{"attributes.updated_at": "desc"}],
    "resource_types": ["rules", "rule_components", "data_elements", "extensions"]
  }
}
```

### Rule component → Rule resolution (two strategies, run in parallel)

Some search results populate `relationships.rule.data.id` (Strategy A),
others only have `links.rules` (Strategy B). Always try both:
- **A**: `GET /rules/{relationships.rule.data.id}`
- **B**: `GET {links.rules}` → paginated list, take first result

Use `ThreadPoolExecutor(max_workers=8)` to fetch concurrently.

### setVariables settings parsing

The `trackerProperties` object has inconsistent structure across property versions:
- Keys may be `evars` or `eVars` — always do case-insensitive lookup.
- Values may be a flat list OR a nested dict: `{"evars": [...]}`.
- Variable values are either constant strings or data element tokens (`%elementName%`).
- Events often have empty values — that's normal.

Deduplicate by `(source_type, rule_id)` since a rule can match via multiple components.

### Pagination

Follow `links.next` until absent. Pass `params=None` on subsequent requests —
the full URL already contains the pagination token.

### Company ID

`GET /companies` → `data[0].id` (format: `COabc123`). Cache on service instance.

---

## Caching Strategy

### Per-key TTL (file-based JSON cache)

Store cache and metadata separately (`{name}.json` + `{name}_meta.json`).
Track TTL per key, not globally:
- Slow-changing config (dimensions, events, processing rules, channels): 24 hours
- Dynamic data (trends, queries): 1 hour

Metadata structure:
```json
{
  "keys": {
    "dimensions": {"created": "2024-01-15T10:30:00", "ttl_hours": 24}
  }
}
```

Handle legacy files (global `created` only) by falling back to 1-hour TTL.

### Background cache warming

Use APScheduler `BackgroundScheduler`. Run immediately at startup, repeat every 24h.
Guard against Flask dev reloader double-start (check for existing jobs before adding).

---

## Architecture

### Hybrid API: always both 2.0 and 1.4

Even on a 2.0 project, keep 1.4 credentials and a 1.4 client. Processing rules,
marketing channels, and list variables are only accessible via 1.4.

### Service bundle per client

Bundle all services for a client into one dict or object:
```python
{"config": {...}, "auth": OAuth2Auth, "api_v2": ..., "api_v14": ..., "launch": ..., "cache": ...}
```
Single `OAuth2Auth` instance per client — reused across Analytics 2.0 and Reactor.

### Optional features via config flags

Gate Launch/Target/AEP features behind config flags (`LAUNCH_ENABLED`, etc.) so
the app degrades gracefully when credentials aren't provided.

### Multi-client credential discovery

Use a `secrets/` directory. Each JSON file = one client. Ignore files prefixed with `_`.
Map `client_slug` (derived from filename) to `/{slug}/` URL prefix.

---

## Security

- Never log credentials or tokens.
- Store credentials in JSON files outside the repo (`.gitignore` the secrets dir).
- Cache OAuth2 tokens in memory only — never persist to disk.
- WSSE: fresh nonce + timestamp per request (no replay risk).
- Request only the minimum OAuth2 scopes needed for your feature set.

---

## Verification

Always include a `verify_setup.py` script that checks:
- Config files exist and parse as valid JSON
- All required keys are present
- Cache/export directories are writable
- Credentials load without error
- (Optional) A live API ping succeeds

Run `uv run verify_setup.py` after changes and before committing.
