# Adobe Analytics 2.0 API Migration Plan

## Executive Summary

This document provides a comprehensive plan for migrating the Codex application from Adobe Analytics API 1.4 (using WSSE authentication) to Adobe Analytics API 2.0 (using OAuth2/JWT authentication). The migration will enable continued support as Adobe phases out the legacy 1.4 API.

**Current State:**
- Python Flask application using Adobe Analytics API 1.4
- WSSE authentication with username/shared secret
- Direct HTTP requests implementation (no third-party library)
- 8 API methods serving configuration data for report suites

**Target State:**
- Adobe Analytics API 2.0 with OAuth2 authentication
- Adobe I/O Console project integration
- Choice between using a Python package or direct API calls
- Equivalent or enhanced functionality for all current features

---

## 1. Adobe I/O Console Project Setup

### Prerequisites
- Adobe Experience Cloud organization administrator access
- Adobe Analytics product profile with appropriate permissions
- Access to Adobe I/O Console (https://console.adobe.io/)

### Step-by-Step Setup Process

#### 1.1 Create Adobe I/O Project

1. **Navigate to Adobe I/O Console**
   - Go to https://console.adobe.io/
   - Sign in with your Adobe ID

2. **Create a New Project**
   - Click "Create new project" button
   - Select "Add API" from the project dashboard

3. **Add Adobe Analytics API**
   - In the API catalog, select "Adobe Analytics"
   - Choose "Analytics 2.0 API"
   - Click "Next"

#### 1.2 Configure Authentication

**Choose Authentication Type:**

For automated server-to-server applications (recommended for Codex):

**Option A: OAuth Server-to-Server (Recommended)**
1. Select "OAuth Server-to-Server" credential type
2. This is the modern replacement for JWT credentials
3. No certificate management required
4. Automatic token refresh capability

**Option B: Service Account (JWT) - Legacy**
1. Generate a public/private key pair:
   ```bash
   openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 \
     -keyout private.key -out certificate.crt
   ```
2. Upload `certificate.crt` to the console
3. Keep `private.key` secure - never commit to version control

#### 1.3 Configure Product Profiles

1. **Select Product Profiles**
   - Choose the Adobe Analytics product profile(s) with appropriate permissions
   - Required permissions:
     - Report Suite Tools: Read access
     - Report Suite Settings: Read access (for configuration data)
     - Company Tools: Read access (for report suite lists)

2. **Save Configuration**
   - Click "Save configured API"
   - Project is now created with credentials

#### 1.4 Gather Required Credentials

From the project overview page, collect:

1. **Client ID** (API Key)
   - Found under "Credentials" section
   - Public identifier for your application

2. **Client Secret**
   - Found under "Credentials" section
   - Keep this secure - treat like a password

3. **Organization ID** (Global Company ID)
   - Found in project overview
   - Format: `{orgId}@AdobeOrg`

4. **Technical Account ID** (for JWT only)
   - Found under Service Account (JWT) credentials
   - Format: `{techAcctId}@techacct.adobe.com`

5. **Technical Account Email** (for JWT only)
   - Associated email for the technical account

#### 1.5 Test API Access

Use the Adobe I/O Console API Explorer:
1. Navigate to your project's API section
2. Use the "Try it" feature to test endpoints
3. Verify you can access:
   - `/api/{globalCompanyId}/collections/suites` (report suites)
   - `/api/{globalCompanyId}/dimensions` (dimensions)

---

## 2. Credentials & OAuth Setup

### 2.1 Configuration File Structure

Update `config.json` to support OAuth2 authentication:

```json
{
  "APP_TITLE": "<COMPANY NAME>",
  "AW_REPORTSUITE_ID": "<RSID>",
  
  "AUTH_METHOD": "oauth2",
  
  "OAUTH2": {
    "CLIENT_ID": "<YOUR_CLIENT_ID>",
    "CLIENT_SECRET": "<YOUR_CLIENT_SECRET>",
    "ORG_ID": "<YOUR_ORG_ID>@AdobeOrg",
    "SCOPES": [
      "openid",
      "AdobeID",
      "read_organizations",
      "additional_info.projectedProductContext",
      "additional_info.roles"
    ]
  },
  
  "JWT": {
    "CLIENT_ID": "<YOUR_CLIENT_ID>",
    "CLIENT_SECRET": "<YOUR_CLIENT_SECRET>",
    "ORG_ID": "<YOUR_ORG_ID>@AdobeOrg",
    "TECHNICAL_ACCOUNT_ID": "<YOUR_TECH_ACCT_ID>@techacct.adobe.com",
    "TECHNICAL_ACCOUNT_EMAIL": "<YOUR_TECH_ACCT_EMAIL>",
    "PRIVATE_KEY_PATH": "./private.key",
    "SCOPES": [
      "https://ims-na1.adobelogin.com/s/ent_analytics_bulk_ingest_sdk"
    ]
  },
  
  "LEGACY_WSSE": {
    "USERNAME": "<WSSE USERNAME:ORG NAME>",
    "SECRET": "<WSSE SECRET>"
  }
}
```

### 2.2 OAuth2 Token Management

**Token Acquisition Flow:**

1. **Server-to-Server OAuth2** (Recommended)
   ```
   POST https://ims-na1.adobelogin.com/ims/token/v3
   
   Request Body (form-encoded):
   - grant_type: client_credentials
   - client_id: {CLIENT_ID}
   - client_secret: {CLIENT_SECRET}
   - scope: openid,AdobeID,read_organizations
   
   Response:
   {
     "access_token": "eyJ...",
     "token_type": "bearer",
     "expires_in": 86399
   }
   ```

2. **JWT Token Exchange** (Legacy, but still supported)
   ```
   Step 1: Generate JWT
   - Create JWT with claims (iss, sub, aud, exp)
   - Sign with private key using RS256
   
   Step 2: Exchange for Access Token
   POST https://ims-na1.adobelogin.com/ims/exchange/jwt
   
   Request Body (form-encoded):
   - client_id: {CLIENT_ID}
   - client_secret: {CLIENT_SECRET}
   - jwt_token: {SIGNED_JWT}
   
   Response:
   {
     "access_token": "eyJ...",
     "token_type": "bearer",
     "expires_in": 86399
   }
   ```

### 2.3 Token Caching Strategy

Implement token caching to minimize authentication requests:

```python
class TokenCache:
    """Cache access tokens with expiration"""
    def __init__(self):
        self.token = None
        self.expires_at = None
    
    def get_token(self, auth_service):
        """Get valid token, refresh if expired"""
        if self.token and self.expires_at > datetime.now():
            return self.token
        
        # Token expired or doesn't exist, fetch new one
        self.token, self.expires_at = auth_service.fetch_token()
        return self.token
```

### 2.4 Security Best Practices

1. **Never commit secrets to version control**
   - Add `config.json`, `private.key` to `.gitignore`
   - Use environment variables or secret management in production

2. **Rotate credentials regularly**
   - Client secrets should be rotated every 90 days
   - JWT certificates should be rotated annually

3. **Use least-privilege access**
   - Only grant necessary product profile permissions
   - Avoid using admin accounts for API access

4. **Secure token storage**
   - Store tokens in memory, not disk
   - Clear tokens on application shutdown
   - Use HTTPS for all API communications

---

## 3. Review of Available Python Packages

### 3.1 Adobe Analytics 2.0 Python Packages

#### Package 1: `aanalytics2` (Recommended)

**Repository:** https://github.com/pitchmuc/aanalytics2
**PyPI:** `aanalytics2`

**Features:**
- Full support for Adobe Analytics 2.0 API
- OAuth2 and JWT authentication
- Methods for dimensions, metrics, segments, calculated metrics
- Report Suite configuration methods
- Active development and community support
- Good documentation and examples

**Pros:**
- Comprehensive API coverage
- Abstracts authentication complexity
- Handles token refresh automatically
- Well-maintained by active contributor
- Used by Adobe Analytics community

**Cons:**
- Additional dependency to manage
- Learning curve for library-specific patterns
- May include features not needed for Codex

**Installation:**
```bash
pip install aanalytics2
```

**Basic Usage:**
```python
import aanalytics2 as api2

# Configure with OAuth2
api2.configure(
    org_id="myorg@AdobeOrg",
    tech_id="techacct@adobe.com",
    secret="CLIENT_SECRET",
    client_id="CLIENT_ID",
    path_to_key="private.key"
)

# Get dimensions for a report suite
dimensions = api2.getDimensions(rsid="your-rsid")
```

#### Package 2: `adobe-analytics-api`

**Repository:** https://github.com/SaturnFromTitan/adobe_analytics
**PyPI:** `adobe-analytics`

**Features:**
- Older package, primarily for 1.4 API
- Limited 2.0 API support
- May be deprecated or unmaintained

**Status:** Not recommended for new projects targeting 2.0 API

#### Package 3: Direct API Implementation (Current Approach)

**Features:**
- Full control over implementation
- No external dependencies beyond `requests`
- Custom error handling and retry logic
- Minimal overhead

**Pros:**
- No third-party library dependencies
- Complete control over behavior
- Easier to debug and customize
- Smaller attack surface

**Cons:**
- More code to maintain
- Manual authentication implementation
- Need to handle API changes manually
- More initial development time

### 3.2 Comparison Matrix

| Criteria | aanalytics2 | Direct API Implementation |
|----------|-------------|---------------------------|
| **Development Time** | Fast (library handles complexity) | Slower (build from scratch) |
| **Maintenance** | Low (library updates) | Medium (manual updates) |
| **Flexibility** | Medium (library constraints) | High (full control) |
| **Dependencies** | +1 external dependency | None (only requests) |
| **Documentation** | Library docs | Adobe official API docs |
| **Error Handling** | Built-in | Custom implementation |
| **Token Management** | Automatic | Manual implementation |
| **Community Support** | GitHub community | Adobe support forums |
| **Code Volume** | Less code | More code |

---

## 4. Recommendation: Python Package vs Direct API

### 4.1 Recommendation

**Use Direct API Implementation (Continue Current Approach)**

**Rationale:**

1. **Consistency with Current Architecture**
   - Codex already uses direct HTTP requests for 1.4 API
   - Team is familiar with this approach
   - Minimal architectural changes required

2. **Simplicity and Control**
   - No external dependencies beyond `requests`
   - Full control over authentication flow
   - Easier to customize for specific needs
   - Better alignment with "MVP velocity" principle

3. **Security**
   - Smaller attack surface (fewer dependencies)
   - Direct control over credential handling
   - No third-party library security concerns

4. **Maintenance**
   - Adobe Analytics 2.0 API is stable and mature
   - Fewer breaking changes expected
   - Direct implementation is more predictable

5. **Code Quality**
   - Current `AdobeAnalyticsService` is well-structured
   - Authentication can be isolated in a separate module
   - Clear separation of concerns

### 4.2 Implementation Strategy

1. **Phase 1: Add OAuth2 Authentication Module**
   - Create `app/services/adobe_auth.py`
   - Implement OAuth2 token acquisition
   - Implement token caching and refresh
   - Keep WSSE for backward compatibility (optional)

2. **Phase 2: Create Analytics 2.0 Service**
   - Create `app/services/adobe_analytics_v2.py`
   - Implement equivalent methods for 2.0 API
   - Use OAuth2 authentication module
   - Maintain similar method signatures where possible

3. **Phase 3: Update Routes**
   - Switch routes to use new service
   - Minimal changes to route handlers
   - Update configuration loading

4. **Phase 4: Testing & Validation**
   - Test all endpoints with 2.0 API
   - Verify data consistency
   - Performance testing
   - Remove 1.4 dependencies

### 4.3 Fallback Option

If direct implementation becomes too complex or time-consuming:
- **Switch to `aanalytics2` package**
- Re-evaluate after 2-3 sprints of development
- Package can reduce complexity for advanced features

---

## 5. API 1.4 to 2.0 Mapping

### 5.1 Authentication Mapping

| 1.4 API | 2.0 API |
|---------|---------|
| **WSSE Header** | **OAuth2 Bearer Token** |
| `X-WSSE: UsernameToken Username="...", PasswordDigest="...", Nonce="...", Created="..."` | `Authorization: Bearer {access_token}` |
| | `x-api-key: {client_id}` |
| | `x-proxy-global-company-id: {org_id}` |

### 5.2 Endpoint Mapping

| Feature | 1.4 API Method | 2.0 API Endpoint | Notes |
|---------|----------------|------------------|-------|
| **Report Suites** | `Company.GetReportSuites` | `GET /collections/suites` | Returns similar data structure |
| **Props (Traffic Variables)** | `ReportSuite.GetProps` | `GET /collections/suites/{rsid}` | Props included in suite details |
| | | `GET /dimensions?rsid={rsid}` | Get all dimensions (includes props) |
| **eVars (Conversion Variables)** | `ReportSuite.GetEvars` | `GET /collections/suites/{rsid}` | eVars included in suite details |
| | | `GET /dimensions?rsid={rsid}` | Get all dimensions (includes eVars) |
| **Success Events** | `ReportSuite.GetEvents` | `GET /collections/suites/{rsid}` | Events included in suite details |
| | | `GET /metrics?rsid={rsid}` | Get all metrics (includes events) |
| **List Variables** | `ReportSuite.GetListVariables` | `GET /collections/suites/{rsid}` | Included in suite details |
| **Processing Rules** | `ReportSuite.ViewProcessingRules` | **NO DIRECT EQUIVALENT** | See note below |
| **Marketing Channels** | `ReportSuite.GetMarketingChannels` | `GET /collections/suites/{rsid}` | Included in suite details |
| **Marketing Channel Rules** | `ReportSuite.GetMarketingChannelRules` | `GET /collections/suites/{rsid}` | Included in suite details |

### 5.3 Processing Rules Note

**Important:** Adobe Analytics 2.0 API does **not** provide direct access to processing rules configuration via public APIs. This is a significant gap.

**Alternatives:**

1. **Continue using 1.4 API for Processing Rules**
   - Maintain dual authentication (1.4 + 2.0)
   - Keep existing `get_processing_rules()` method
   - Only migrate other endpoints to 2.0

2. **Use Admin API 1.4 Endpoint**
   - Some admin endpoints may remain available
   - Adobe may provide migration path

3. **Manual Documentation**
   - Export processing rules once
   - Store as static data
   - Update manually when rules change

4. **Contact Adobe Support**
   - Request API access for processing rules
   - May require special permissions or beta access

**Recommended Approach:** Maintain 1.4 API access for processing rules until Adobe provides 2.0 equivalent.

### 5.4 Request/Response Structure Changes

#### 1.4 API Request Pattern:
```python
POST https://api.omniture.com/admin/1.4/rest/?method=ReportSuite.GetEvars

Headers:
- X-WSSE: {wsse_header}
- Content-Type: application/json

Body:
{
  "rsid_list": ["my-rsid"]
}

Response:
[
  {
    "rsid": "my-rsid",
    "evars": [
      {
        "id": "evar1",
        "name": "Campaign ID",
        "type": "text string",
        ...
      }
    ]
  }
]
```

#### 2.0 API Request Pattern:
```python
GET https://analytics.adobe.io/api/{globalCompanyId}/dimensions?rsid=my-rsid&classifiable=true

Headers:
- Authorization: Bearer {access_token}
- x-api-key: {client_id}
- x-proxy-global-company-id: {org_id}

Response:
{
  "content": [
    {
      "id": "variables/evar1",
      "name": "Campaign ID",
      "type": "string",
      ...
    }
  ],
  "totalPages": 1,
  "totalElements": 250,
  "number": 0
}
```

### 5.5 Data Model Mapping

#### eVars Example:

**1.4 API Response:**
```json
{
  "id": "evar1",
  "name": "Campaign ID",
  "type": "text string",
  "expiration_type": "days",
  "expiration_custom_days": 30,
  "allocation_type": "most recent",
  "description": "Marketing campaign identifier"
}
```

**2.0 API Response:**
```json
{
  "id": "variables/evar1",
  "name": "Campaign ID",
  "type": "string",
  "category": "conversion",
  "support": ["oberon", "dataWarehouse"],
  "description": "Marketing campaign identifier",
  "extraTitleInfo": "eVar1"
}
```

**Mapping Required:**
- `id`: Strip `variables/` prefix for consistency
- `type`: Map `string` → `text string`
- Expiration data: May need separate API call or suite settings
- Allocation type: May need separate API call or suite settings

---

## 6. High-Level Code Changes Summary

### 6.1 Files to Create

1. **`app/services/adobe_auth.py`** (New)
   - OAuth2/JWT authentication implementation
   - Token acquisition and refresh
   - Token caching with expiration
   - Multiple auth method support

2. **`app/services/adobe_analytics_v2.py`** (New)
   - Adobe Analytics 2.0 API service
   - Equivalent methods to current service
   - Uses `adobe_auth` for authentication
   - Handles 2.0 API response formats

### 6.2 Files to Modify

1. **`config.dist.json`** and `config.json`
   ```json
   {
     "APP_TITLE": "Company Name",
     "AW_REPORTSUITE_ID": "rsid",
     
     "AUTH_METHOD": "oauth2",
     
     "OAUTH2": {
       "CLIENT_ID": "...",
       "CLIENT_SECRET": "...",
       "ORG_ID": "...@AdobeOrg"
     }
   }
   ```

2. **`app/routes/main.py`**
   - Update `get_api_service()` function
   - Switch from `AdobeAnalyticsService` to `AdobeAnalyticsV2Service`
   - Minimal logic changes required
   - May need to adjust column mappings if data structure changes

3. **`requirements.txt`**
   - Add `PyJWT>=2.8.0` (if using JWT authentication)
   - Add `cryptography>=41.0.0` (for JWT signing)
   - Keep existing dependencies

4. **`.gitignore`**
   - Add `private.key` (for JWT)
   - Ensure `config.json` is already ignored

5. **`README.md`**
   - Update authentication instructions
   - Document new OAuth2 setup process
   - Update configuration examples

6. **`.github/copilot-instructions.md`**
   - Update Adobe Analytics API version
   - Document new authentication method
   - Update configuration section

### 6.3 New Service Architecture

```
app/services/
├── adobe_auth.py         # NEW: Authentication handling
│   ├── class OAuth2Auth
│   │   ├── __init__(client_id, client_secret, org_id)
│   │   ├── get_access_token() -> str
│   │   └── _fetch_token() -> (token, expires_at)
│   │
│   └── class JWTAuth  # Optional, for JWT method
│       ├── __init__(client_id, client_secret, private_key_path, ...)
│       ├── get_access_token() -> str
│       ├── _generate_jwt() -> str
│       └── _exchange_jwt_for_token(jwt) -> (token, expires_at)
│
├── adobe_analytics_v2.py  # NEW: 2.0 API implementation
│   └── class AdobeAnalyticsV2Service
│       ├── __init__(auth_service, org_id)
│       ├── _make_request(endpoint, method, params) -> dict
│       ├── get_report_suites() -> list[dict]
│       ├── get_props(rsid) -> list[dict]
│       ├── get_evars(rsid) -> list[dict]
│       ├── get_success_events(rsid) -> list[dict]
│       ├── get_list_variables(rsid) -> list[dict]
│       ├── get_marketing_channels(rsid) -> list[dict]
│       └── get_marketing_channel_rules(rsid) -> list[dict]
│
├── adobe_analytics.py     # KEEP: Legacy 1.4 API (for processing rules)
│   └── class AdobeAnalyticsService
│       ├── get_processing_rules(rsid) -> list[dict]
│       └── ... (keep existing methods as fallback)
│
└── cache.py              # NO CHANGES NEEDED
    └── class CacheService
```

### 6.4 Migration Approach

**Recommended Strategy: Gradual Migration with Feature Flag**

#### Phase 1: Implement OAuth2 Authentication (Week 1)
- Create `adobe_auth.py`
- Implement OAuth2 token acquisition
- Add configuration support
- Write unit tests for authentication

#### Phase 2: Create 2.0 API Service (Week 2)
- Create `adobe_analytics_v2.py`
- Implement core methods (props, evars, events)
- Add response transformation logic
- Test against live API

#### Phase 3: Implement Advanced Features (Week 3)
- List variables support
- Marketing channels and rules
- Report suites listing
- Handle pagination if needed

#### Phase 4: Route Integration (Week 4)
- Add feature flag to switch between 1.4 and 2.0
- Update route handlers
- Test all endpoints
- Fix data transformation issues

#### Phase 5: Processing Rules Strategy (Week 5)
- Evaluate processing rules API availability
- Implement hybrid approach (1.4 + 2.0)
- Document limitations
- Update UI if needed

#### Phase 6: Cleanup and Documentation (Week 6)
- Remove feature flag (commit to 2.0)
- Update all documentation
- Create migration guide
- Deploy to production

### 6.5 Code Example: OAuth2 Authentication

```python
# app/services/adobe_auth.py

import requests
from datetime import datetime, timedelta
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class OAuth2Auth:
    """OAuth2 authentication for Adobe Analytics 2.0 API"""
    
    TOKEN_ENDPOINT = "https://ims-na1.adobelogin.com/ims/token/v3"
    
    def __init__(self, client_id: str, client_secret: str, scopes: list[str] = None):
        """
        Initialize OAuth2 authentication
        
        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            scopes: List of OAuth2 scopes (optional)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or ["openid", "AdobeID", "read_organizations"]
        
        # Token cache
        self._access_token = None
        self._token_expires_at = None
    
    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary
        
        Returns:
            Valid access token string
        """
        # Return cached token if still valid (with 5 min buffer)
        if self._access_token and self._token_expires_at:
            buffer_time = datetime.now() + timedelta(minutes=5)
            if buffer_time < self._token_expires_at:
                logger.debug("Using cached access token")
                return self._access_token
        
        # Fetch new token
        logger.info("Fetching new access token")
        self._access_token, self._token_expires_at = self._fetch_token()
        return self._access_token
    
    def _fetch_token(self) -> Tuple[str, datetime]:
        """
        Fetch a new access token from Adobe IMS
        
        Returns:
            Tuple of (access_token, expiration_datetime)
        """
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": ",".join(self.scopes)
        }
        
        response = requests.post(
            self.TOKEN_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        
        data = response.json()
        access_token = data["access_token"]
        expires_in = data.get("expires_in", 86399)  # Default ~24 hours
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        logger.info("Access token acquired, expires at %s", expires_at)
        return access_token, expires_at
```

### 6.6 Code Example: 2.0 API Service

```python
# app/services/adobe_analytics_v2.py

import requests
import logging
from typing import Any
from app.services.adobe_auth import OAuth2Auth

logger = logging.getLogger(__name__)


class AdobeAnalyticsV2Service:
    """Service for Adobe Analytics 2.0 API"""
    
    API_BASE = "https://analytics.adobe.io/api"
    
    def __init__(self, auth_service: OAuth2Auth, org_id: str):
        """
        Initialize Adobe Analytics 2.0 service
        
        Args:
            auth_service: Authentication service instance
            org_id: Organization ID (format: {orgId}@AdobeOrg)
        """
        self.auth = auth_service
        self.org_id = org_id
        self.global_company_id = org_id  # May need transformation
    
    def _make_request(self, endpoint: str, method: str = "GET", 
                     params: dict = None, json_data: dict = None) -> Any:
        """
        Make authenticated request to Adobe Analytics 2.0 API
        
        Args:
            endpoint: API endpoint (e.g., "/dimensions")
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            json_data: JSON request body
            
        Returns:
            JSON response data
        """
        url = f"{self.API_BASE}/{self.global_company_id}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.auth.get_access_token()}",
            "x-api-key": self.auth.client_id,
            "x-proxy-global-company-id": self.org_id,
            "Content-Type": "application/json"
        }
        
        logger.debug("API request: %s %s", method, url)
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data
        )
        response.raise_for_status()
        
        return response.json()
    
    def get_evars(self, rsid: str) -> list[dict]:
        """
        Get eVars (conversion variables) for a report suite
        
        Args:
            rsid: Report suite ID
            
        Returns:
            List of eVar configurations
        """
        # Get dimensions filtered to eVars
        response = self._make_request(
            "/dimensions",
            params={
                "rsid": rsid,
                "classifiable": "true"
            }
        )
        
        dimensions = response.get("content", [])
        
        # Filter to eVars and transform to 1.4 format
        evars = []
        for dim in dimensions:
            if dim["id"].startswith("variables/evar"):
                evar_num = dim["id"].replace("variables/evar", "evar")
                evars.append({
                    "id": evar_num,
                    "name": dim.get("name", ""),
                    "type": dim.get("type", "string"),
                    "description": dim.get("description", ""),
                    # Note: expiration and allocation may need separate API call
                })
        
        return evars
    
    # Similar methods for get_props(), get_success_events(), etc.
```

### 6.7 Configuration Changes

```json
{
  "APP_TITLE": "Company Name",
  "AW_REPORTSUITE_ID": "your-rsid",
  
  "API_VERSION": "2.0",
  
  "OAUTH2": {
    "CLIENT_ID": "your-client-id-from-console",
    "CLIENT_SECRET": "your-client-secret-from-console",
    "ORG_ID": "your-org-id@AdobeOrg",
    "SCOPES": ["openid", "AdobeID", "read_organizations"]
  }
}
```

### 6.8 Route Updates

```python
# app/routes/main.py (modified)

from app.services.adobe_auth import OAuth2Auth
from app.services.adobe_analytics_v2 import AdobeAnalyticsV2Service


def get_api_service() -> AdobeAnalyticsV2Service:
    """Get configured Adobe Analytics 2.0 service"""
    # Create auth service
    auth = OAuth2Auth(
        client_id=current_app.config['OAUTH2']['CLIENT_ID'],
        client_secret=current_app.config['OAUTH2']['CLIENT_SECRET'],
        scopes=current_app.config['OAUTH2']['SCOPES']
    )
    
    # Create API service
    return AdobeAnalyticsV2Service(
        auth_service=auth,
        org_id=current_app.config['OAUTH2']['ORG_ID']
    )

# All other route handlers remain unchanged!
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

Create tests for authentication and API methods:

```python
# tests/test_adobe_auth.py
def test_oauth2_token_acquisition()
def test_token_caching()
def test_token_refresh()

# tests/test_adobe_analytics_v2.py
def test_get_evars()
def test_get_props()
def test_response_transformation()
```

### 7.2 Integration Tests

Test against Adobe Analytics sandbox/dev environment:
- Verify all endpoints return expected data
- Test with different report suites
- Validate error handling

### 7.3 Manual Testing Checklist

- [ ] OAuth2 authentication works
- [ ] All tabs load without errors
- [ ] Props display correctly
- [ ] eVars display correctly
- [ ] Events display correctly
- [ ] List variables display correctly
- [ ] Marketing channels display correctly
- [ ] Channel rules display correctly
- [ ] CSV exports work
- [ ] Cache functionality works
- [ ] Error messages are user-friendly

---

## 8. Risk Analysis

### 8.1 High Risk Items

1. **Processing Rules Not Available in 2.0 API**
   - **Impact:** High - Core feature may be unavailable
   - **Mitigation:** Maintain 1.4 API for this endpoint only
   - **Alternative:** Manual documentation approach

2. **Data Structure Differences**
   - **Impact:** Medium - May require significant transformation logic
   - **Mitigation:** Build comprehensive mapping layer
   - **Testing:** Extensive comparison between 1.4 and 2.0 responses

3. **Authentication Complexity**
   - **Impact:** Medium - OAuth2 more complex than WSSE
   - **Mitigation:** Use well-tested authentication module
   - **Testing:** Thorough testing of token refresh scenarios

### 8.2 Medium Risk Items

1. **API Rate Limits**
   - **Impact:** Medium - Different limits than 1.4 API
   - **Mitigation:** Implement retry logic with exponential backoff
   - **Monitoring:** Log rate limit headers

2. **Expiration/Allocation Data**
   - **Impact:** Medium - May not be in dimensions endpoint
   - **Mitigation:** Make additional API calls if needed
   - **Alternative:** Remove from display if unavailable

3. **Breaking Changes**
   - **Impact:** Low - 2.0 API is stable
   - **Mitigation:** Monitor Adobe release notes
   - **Testing:** Regular integration tests

---

## 9. Timeline Estimate

### 9.1 Development Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **1. Setup & Authentication** | 1 week | OAuth2 module, config updates |
| **2. Core API Methods** | 1 week | Props, eVars, events methods |
| **3. Advanced Features** | 1 week | List vars, channels, rules |
| **4. Route Integration** | 1 week | Updated routes, testing |
| **5. Processing Rules** | 1 week | Hybrid approach implementation |
| **6. Documentation & Cleanup** | 1 week | Docs, deployment guide |

**Total Estimated Duration:** 6 weeks (1.5 months)

### 9.2 Parallel Work Opportunities

- Documentation can be written alongside development
- Testing can begin as soon as OAuth2 is implemented
- UI updates (if any) can be designed early

---

## 10. Success Criteria

### 10.1 Functional Requirements

- [ ] All current features work with 2.0 API
- [ ] OAuth2 authentication is reliable and secure
- [ ] Token refresh happens automatically
- [ ] All data displays match current implementation
- [ ] CSV exports work correctly
- [ ] Cache functionality is preserved
- [ ] Processing rules have a working solution

### 10.2 Non-Functional Requirements

- [ ] API response times are acceptable (< 2 seconds)
- [ ] Token acquisition is fast (< 1 second)
- [ ] No secrets in source control
- [ ] Error messages are clear and actionable
- [ ] Logging provides adequate troubleshooting info
- [ ] Documentation is comprehensive

### 10.3 Acceptance Testing

- [ ] Product owner can successfully configure OAuth2
- [ ] All report suite data displays correctly
- [ ] Exports match expected format
- [ ] Application is stable for 1 week without crashes
- [ ] Performance is equivalent to 1.4 API version

---

## 11. Rollback Plan

### 11.1 Rollback Strategy

If migration encounters blocking issues:

1. **Immediate Rollback**
   - Feature flag to switch back to 1.4 API
   - Keep 1.4 code in repository during migration
   - Separate branch for 2.0 development

2. **Configuration-Based Rollback**
   ```json
   {
     "API_VERSION": "1.4",  // Change to "2.0" when ready
     ...
   }
   ```

3. **Gradual Rollback**
   - Rollback individual endpoints if needed
   - Keep working endpoints on 2.0
   - Fix problematic endpoints

### 11.2 Rollback Triggers

- Authentication failures > 10% of requests
- Data accuracy issues discovered
- Performance degradation > 50%
- Critical feature unavailable (e.g., processing rules)
- Security vulnerability discovered

---

## 12. Post-Migration Checklist

### 12.1 Immediate Post-Migration (Week 1)

- [ ] Monitor error logs for authentication issues
- [ ] Verify data accuracy against 1.4 API
- [ ] Check API usage/rate limiting
- [ ] Gather user feedback
- [ ] Document any issues

### 12.2 Short-Term (Month 1)

- [ ] Remove 1.4 API code (if no longer needed)
- [ ] Update all documentation
- [ ] Train users on any changes
- [ ] Optimize token refresh logic
- [ ] Fine-tune error handling

### 12.3 Long-Term (Quarter 1)

- [ ] Evaluate new 2.0 API features
- [ ] Consider adding new functionality
- [ ] Review and optimize performance
- [ ] Update security practices
- [ ] Plan for future API updates

---

## 13. Resources & References

### 13.1 Official Documentation

- [Adobe Analytics 2.0 API Guide](https://developer.adobe.com/analytics-apis/docs/2.0/)
- [Adobe I/O Console](https://console.adobe.io/)
- [OAuth Server-to-Server Authentication](https://developer.adobe.com/developer-console/docs/guides/authentication/ServerToServerAuthentication/)
- [JWT Authentication Guide](https://developer.adobe.com/developer-console/docs/guides/authentication/JWT/)

### 13.2 Python Package Documentation

- [aanalytics2 GitHub](https://github.com/pitchmuc/aanalytics2)
- [aanalytics2 Documentation](https://github.com/pitchmuc/aanalytics2/wiki)

### 13.3 Adobe Support

- [Adobe Analytics API Forum](https://experienceleaguecommunities.adobe.com/t5/adobe-analytics-apis/ct-p/adobe-analytics-apis)
- [Adobe Developer Support](https://developer.adobe.com/support/)

### 13.4 Internal Resources

- Current implementation: `/app/services/adobe_analytics.py`
- API 1.4 Swagger: `/docs/adobe_analytics_api_1.4_swagger.json`
- API 2.0 Swagger: `/docs/adobe_analytics_api_2.0_swagger.json`
- GitHub repository: `maxisdigital/codex`

---

## 14. Questions & Decisions Log

### 14.1 Open Questions

1. **Q:** Do we have access to Adobe Analytics API 2.0 in our organization?
   **A:** Yes

2. **Q:** What permissions does our technical account need?
   **A:** [TO BE DETERMINED]

3. **Q:** Are there any reporting requirements that need 1.4 API?
   **A:** [TO BE DETERMINED - Processing Rules]

4. **Q:** Do we need backward compatibility with 1.4 API?
   **A:** Yes for processing rules

### 14.2 Decision Log

| Date | Decision | Rationale | Owner |
|------|----------|-----------|-------|
| TBD | Use direct API vs package | Consistency, control, security | TBD |
| TBD | OAuth2 vs JWT | OAuth2 recommended by Adobe | TBD |
| TBD | Processing rules strategy | API availability | TBD |

---

## 15. Next Steps

### 15.1 Immediate Actions

1. **Review this migration plan** with team and stakeholders
2. **Create Adobe I/O Console project** following Section 1
3. **Gather credentials** and test API access
4. **Assign GitHub Copilot tasks** using sections as work items
5. **Set up development environment** with test credentials

### 15.2 GitHub Copilot Task Breakdown

This plan is structured to be assigned to GitHub Copilot in phases:

**Task 1: OAuth2 Authentication Module**
- Input: Section 2 (OAuth Setup) + Section 6.5 (Code Example)
- Output: `app/services/adobe_auth.py`

**Task 2: Analytics 2.0 API Service**
- Input: Section 5 (API Mapping) + Section 6.6 (Code Example)
- Output: `app/services/adobe_analytics_v2.py`

**Task 3: Configuration Updates**
- Input: Section 6.7 (Configuration Changes)
- Output: Updated `config.dist.json`, `.gitignore`

**Task 4: Route Integration**
- Input: Section 6.8 (Route Updates)
- Output: Modified `app/routes/main.py`

**Task 5: Testing Implementation**
- Input: Section 7 (Testing Strategy)
- Output: Test files and test execution

**Task 6: Documentation Updates**
- Input: Sections 1-2 (Setup instructions)
- Output: Updated README.md, copilot-instructions.md

---

## Appendix A: API Response Examples

### A.1 Report Suites

**1.4 API Response:**
```json
{
  "report_suites": [
    {
      "rsid": "example-rsid",
      "site_title": "Example Site",
      "virtual_rsid": false
    }
  ]
}
```

**2.0 API Response:**
```json
{
  "content": [
    {
      "rsid": "example-rsid",
      "name": "Example Site",
      "parentRsid": null,
      "currency": "USD",
      "calendarType": {
        "type": "gregorian",
        "anchorDate": "1/1"
      }
    }
  ],
  "totalElements": 1
}
```

### A.2 Dimensions (eVars/Props)

**2.0 API Response:**
```json
{
  "content": [
    {
      "id": "variables/evar1",
      "name": "Campaign ID",
      "description": "Marketing campaign identifier",
      "type": "string",
      "category": "conversion",
      "support": ["oberon", "dataWarehouse"],
      "pathable": false,
      "extraTitleInfo": "eVar1",
      "segmentable": true,
      "reportable": ["oberon", "dataWarehouse"]
    },
    {
      "id": "variables/prop1",
      "name": "Page Section",
      "description": "Website section",
      "type": "string",
      "category": "traffic",
      "support": ["oberon"],
      "pathable": true,
      "extraTitleInfo": "Prop1",
      "segmentable": true
    }
  ],
  "totalPages": 1,
  "totalElements": 250,
  "numberOfElements": 250,
  "number": 0,
  "firstPage": true,
  "lastPage": true
}
```

### A.3 Metrics (Events)

**2.0 API Response:**
```json
{
  "content": [
    {
      "id": "metrics/event1",
      "name": "Product Views",
      "description": "Number of product detail page views",
      "type": "int",
      "category": "conversion",
      "support": ["oberon", "dataWarehouse"],
      "extraTitleInfo": "Event1",
      "segmentable": true,
      "polarity": "positive"
    }
  ],
  "totalPages": 1,
  "totalElements": 1000
}
```

---

## Appendix B: Error Handling Examples

### B.1 Authentication Errors

```python
def handle_auth_error(error):
    """Handle authentication errors gracefully"""
    if error.status_code == 401:
        logger.error("Authentication failed: Invalid credentials")
        return "Authentication failed. Please check your OAuth2 credentials."
    elif error.status_code == 403:
        logger.error("Authorization failed: Insufficient permissions")
        return "Access denied. Your account needs additional permissions."
    else:
        logger.error("Unexpected auth error: %s", error)
        return "Authentication error. Please try again later."
```

### B.2 Rate Limiting

```python
def handle_rate_limit(response):
    """Handle rate limit responses"""
    if response.status_code == 429:
        retry_after = response.headers.get('Retry-After', 60)
        logger.warning("Rate limit exceeded. Retry after %s seconds", retry_after)
        time.sleep(int(retry_after))
        return True  # Retry
    return False  # Don't retry
```

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **OAuth2** | Industry-standard protocol for authorization |
| **JWT** | JSON Web Token, used for authentication claims |
| **Bearer Token** | Access token passed in Authorization header |
| **Global Company ID** | Organization identifier in Adobe Analytics 2.0 |
| **RSID** | Report Suite ID |
| **WSSE** | Web Services Security (legacy auth method) |
| **IMS** | Adobe Identity Management Service |
| **Product Profile** | Permission set in Adobe Admin Console |
| **Scope** | OAuth2 permission requested by application |

---

**Document Version:** 1.0
**Last Updated:** December 2024
**Author:** GitHub Copilot Migration Planning Agent
**Status:** Ready for Implementation

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2024-12 | 1.0 | Initial migration plan created | GitHub Copilot |

