# GitHub Copilot Instructions for Codex Project

## Project Overview

**Codex** is a Python/Flask application that visualizes Adobe Analytics configurations (eVars, Props, Events, processing rules, marketing channel settings). It is a port of [RShiny SDR](https://github.com/Brontojoris/rshiny-sdr).

**Key Objectives:**
- Display configuration of Conversion Variables (eVars), Traffic Variables (props), Success Events, ListVars
- Display Processing Rules, Marketing Channel Rules, and key settings
- Health checks for events and critical implementation components
- Top values for eVars/props to validate naming, cardinality, and usage
- Quick configuration snapshots for documentation and audits

## Architecture & Tech Stack

- **Framework**: Flask (`app/routes/`, `app/templates/`)
- **Frontend**: Server-side rendered Jinja2 templates
- **Data Source**: Hybrid Adobe Analytics APIs
  - **API 2.0 (default)** via OAuth2 (`adobe_auth.py`, `adobe_analytics_v2.py`)
  - **API 1.4 (legacy)** via WSSE (`adobe_analytics.py`) for endpoints still unavailable in 2.0 (e.g., processing rules)
- **Service Layer**:
  - `app/services/adobe_analytics_v2.py`: OAuth2-backed Analytics 2.0 client
  - `app/services/adobe_analytics.py`: Legacy 1.4 client (manually constructs X-WSSE header)
  - `app/services/adobe_auth.py`: OAuth2 token acquisition and caching
  - `app/services/cache.py`: JSON file-based caching (hourly expiry)
- **Package/Env Management**: `uv` (`pyproject.toml`, `uv.lock`)
- **Runtime/Dependencies**: Python 3.13+, `flask`, `requests`

## User & Developer Context (Crucial)

- **User Profile**: Strong JavaScript background, **Beginner in Python**
  - *Action*: Explain Python concepts clearly. Avoid overly "pythonic" code if a JS-style approach is readable.
- **Philosophy**: **Post MVP Velocity**. We are now working on version 2. There should be more emphasis on architechture and scaling for future enhancements. Watch for opportunities to refactor and simplify code.
  - *Testing*: Currently there is only **Manual testing**. No unit tests. Reliant on `verify_setup.py`. Devise a testing strategy that is **fast and reliable**.

## Build, Test, and Verification Procedures

### Setup and Installation
```bash
# Install/sync dependencies
uv sync
```

### Running the Application
```bash
# Start Flask development server
uv run run.py

# Default: http://127.0.0.1:5010
# Custom port: PORT=5011 uv run run.py
```

### Health Check
```bash
# Verify setup (checks config, directories, imports)
uv run verify_setup.py
```

### Testing Strategy
**Important**: This project is transitioning beyond MVP. While there is currently **no formal test suite**, the goal is to devise a fast and reliable testing strategy as part of post-MVP development.

**Manual Testing Workflow:**
1. Run `uv run verify_setup.py` to check basic health
2. Start the application with `uv run run.py`
3. Test changes by navigating through the web interface
4. Verify exports work by checking the `exports/` directory

**When Making Changes:**
- Always test by running the application manually
- Verify all Flask routes still load without errors
- Check that Adobe Analytics API service methods return expected data
- Ensure exports directory is writable and exports complete

### Jupyter Notebook Workflow
```bash
# Start Jupyter
uv run jupyter notebook

# Navigate to notebooks/ directory
# Each notebook is designed to be self-contained
# Test notebook changes by running all cells
```

### Docker Build and Deployment
```bash
# Build and run locally
docker compose up -d --build

# View logs
docker compose logs -f

# Verify exports directory permissions
# Ensure: ./exports:/app/exports:rw in docker-compose.yml
```

### Configuration

Config file: `config.json` (git-ignored). Template: `config.dist.json`.

| Key | Required | Description |
|-----|----------|-------------|
| `APP_TITLE` | Always | Application title |
| `AW_REPORTSUITE_ID` | Always | Report suite ID |
| `API_VERSION` | For 2.0 | Set to `"2.0"` |
| `CLIENT_ID` | For 2.0 | OAuth2 client ID |
| `CLIENT_SECRET` | For 2.0 | OAuth2 client secret |
| `ORGANIZATION_ID` | For 2.0 | Adobe org ID |
| `SCOPES` | Optional | OAuth2 scopes |
| `AW_USERNAME` | For 1.4 | WSSE username |
| `AW_SECRET` | For 1.4 | WSSE secret |

**Note**: Even with `API_VERSION=2.0`, WSSE credentials are still needed for legacy 1.4-only routes.

### Common Build/Runtime Issues
1. **Missing config.json**: Verify file exists and has required keys
2. **Port already in use**: Try `PORT=5011 uv run run.py`
3. **Import errors**: Run `uv sync`
4. **Docker export errors**: Check volume mount permissions (needs `:rw` flag)

### Security Guidelines

#### Secrets and Credentials
- **CRITICAL**: Never commit `config.json` to version control
- API credentials must be stored in `config.json` (excluded via `.gitignore`)
- Use `.github/workflows/checkout.yml` to generate config in CI/CD environments
- Never log or expose credentials in error messages or debug output

#### Code Safety
- **Input Validation**: Validate all user inputs in Flask routes
- **Dependency Security**: Pin critical dependencies to avoid breaking changes
- Review security advisories before updating major dependencies
- Avoid adding unnecessary external packages

#### Safe API Usage
- **Rate Limiting**: Be mindful of Adobe Analytics API call limits
- **Cache Results**: Store API responses in memory during a session to reduce calls
- **Error Handling**: Handle API errors gracefully without exposing internal details
- **Scope Verification**: Ensure authentication scope matches intended operations (admin vs developer SDK)

#### File System Security
- **Export Directory**: Only write to `exports/` directory
- **Path Validation**: Validate file paths to prevent directory traversal
- **Temporary Files**: Use `/tmp` for any temporary files during development
- Never write to or modify system directories

## Coding & Implementation Guidelines

### API Requests
- **Always** wrap calls with cache: `cache.get_or_set(rsid, key, fetch_function)`
- Use `AdobeAnalyticsV2Service` by default for 2.0-supported resources
- Use `AdobeAnalyticsService` (`get_api_service_v14`) for 1.4-only resources

### Adding New Features
1. Add Service method in the correct service (`adobe_analytics_v2.py` or `adobe_analytics.py`)
2. Add Route (`app/routes/main.py`) with Caching
3. Add Template (`app/templates/`)

### Key Files
| File | Purpose |
|------|---------|
| `app/routes/main.py` | Core application logic and routes |
| `app/services/adobe_analytics_v2.py` | API 2.0 wrapper |
| `app/services/adobe_analytics.py` | API 1.4 wrapper |
| `app/services/adobe_auth.py` | OAuth2 auth/token management |
| `app/services/cache.py` | JSON file-based caching |
| `verify_setup.py` | Local setup and configuration checks |
| `notebooks/` | Exploratory scripts |

## Development Guidelines

### Core Principles

#### 1. Post MVP: Architecture & Scalability First
- **Primary Goal:** Build maintainable, scalable code with a focus on architecture and future enhancements
- **Pragmatism Over Purity:** Choose simple solutions that are also extensible and easy to refactor
- **Watch for Refactoring Opportunities:** Simplify and improve code as the project matures
- **Incremental Improvement:** Expect frequent, small-scale refactoring - code should improve over time

#### 2. Quality-Focused Technical Approach
- **Code Style:** Follow PEP 8; style matters for long-term maintainability
- **Testing:** Work toward a fast and reliable testing strategy; add tests for new features and regressions
- **Documentation:** Inline comments focusing on *what* the code does and *why* specific choices were made
- **Dependencies:** Suggest simplest, most lightweight libraries available
- **Input/Output:** Prioritize simple interfaces (standard I/O, basic JSON/CSV) to quickly prove concepts

#### 3. Naming Conventions
- Use simple, direct names: `process_data`, `user_list`, `temp_result`
- Avoid overly clever or abbreviated names
- Prioritize readability for JavaScript developers learning Python

### Response Behavior

#### General Guidelines
- **Be concise and direct** - answer queries efficiently
- **Use structured formatting** - headings, bullet points for clarity
- **Highlight key information** in **bold**
- **Avoid emojis** - maintain neutral, professional tone
- **Ask clarifying questions** only if queries are genuinely ambiguous
- At the conclusion of tasks, summarise the actions taken into a new file at `../docs/autopsies/<issue-number>.md` using existing files in the `./docs/autopsies/` folder as a template.

#### User Context Assumptions
- User has **strong JavaScript background**
- User is **beginner in Python** - explain Python-specific concepts when relevant
- User is familiar with Adobe Launch/Tags but may need API wrapper guidance

#### External Libraries
- **Avoid external libraries** unless there's a clear benefit
- **When recommending libraries:** Describe the benefits explicitly
- **Default to built-in solutions** when possible
- Ensure compatibility with **Python 3.13+**

#### Code Examples
- Provide working, tested code snippets
- Include necessary imports
- Add brief explanatory comments for non-obvious logic
- Show typical output/results when helpful

### Jupyter Notebook Handling

#### Critical Rules

**NEVER directly modify `.ipynb` files** - Jupyter notebooks have complex JSON structure that requires special handling.

**Instead, provide:**
1. **Code snippets** that the user can copy/paste into notebook cells
2. **Step-by-step instructions** for manual implementation
3. **Clear cell organization** suggestions (which code goes in which cell)
4. **Expected outputs** to verify correct implementation

**Example Response Format:**
```python
# Cell 1: Import and configure
import launchpy as lp
lp.importConfigFile('config.json')

# Cell 2: Initialize and retrieve data
admin = lp.Admin()
# ... rest of code

# Expected output:
# Successfully connected to company: [Company Name]
```

#### Notebook Best Practices
- Organize code into logical cell blocks
- Include markdown cell suggestions for documentation
- Recommend using `%load_ext autoreload` for development
- Suggest saving intermediate results to variables for inspection
- Recommend using pandas DataFrames for tabular data exploration

### Error Handling & Debugging

#### Authentication Issues
**Symptom**: "Authentication failed" or 401 errors from API
**Resolution Steps:**
1. Verify `config.json` exists in project root
2. Check API credentials are valid
3. For API 2.0: Verify OAuth2 credentials (`CLIENT_ID`, `CLIENT_SECRET`, `ORGANIZATION_ID`)
4. For API 1.4: Verify WSSE credentials (`AW_USERNAME`, `AW_SECRET`)

#### Common Pitfalls
1. **Missing cache wrapper**: Always use `cache.get_or_set()` for API calls
2. **Wrong API version**: Check if endpoint is available in 2.0 before using 1.4
3. **Stale cache**: Clear `cache/` directory if seeing outdated data

### Code Quality Checklist

For every code suggestion, confirm:
- [ ] Compatible with Python 3.13+
- [ ] Uses existing project dependencies when possible
- [ ] Includes necessary imports
- [ ] Has minimal inline comments explaining non-obvious logic
- [ ] Follows simple, direct naming conventions
- [ ] Prioritizes functionality over perfection
- [ ] API calls wrapped with caching

---

## Additional Resources

For high-level project context and AI agent guidelines, see **[AGENTS.md](../AGENTS.md)** in the repository root.

For post-mortem analysis of completed issues, see **[docs/autopsies/](../docs/autopsies/)**.

---

*Last updated: March 14, 2026*

