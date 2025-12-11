# GitHub Copilot Instructions for Codex Project

## Project Overview

**Codex** is a Python-based project for displaying the configuration of Adobe Analytics eVars, Traffic Variables, Success Events, ListVars, Processing Rules, and Marketing Channels.

It is based on [RShiny SDR](https://github.com/Brontojoris/rshiny-sdr) using the [RSiteCatalyst](https://randyzwitch.com/rsitecatalyst/) package that calls the [Adobe Analytics API 1.4](https://developer.adobe.com/analytics-apis/docs/1.4/) using WSSE authentication.

**Key Objectives:**
- Display configuration of Conversion Variables (eVars), Traffic Variables (props), Success Events, ListVars
- Display Processing Rules, Marketing Channel Rules, and key settings
- Health checks for events and critical implementation components
- Top values for eVars/props to validate naming, cardinality, and usage
- Quick configuration snapshots for documentation and audits

## Technical Context

### Project Dependencies
- **Python 3.13+** (user has JavaScript background, beginner in Python)
- **TO BE DETERMINED** - Adobe Analytics API 1.4 wrapper
- **pandas** (>2.0.0) - Data manipulation and analysis
- **ipywidgets** - Interactive Jupyter notebook widgets
- **ipyleaflet** (>=0.17.0, <1.0.0) - Mapping visualization
- **Flask>=2.0.0**
- **Werkzeug>=3.0.0**

### Build, Test, and Verification Procedures

#### Setup and Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Verify setup (checks imports, config, app structure)
python verify_setup.py
```

#### Running the Application
```bash
# Start Flask development server
python run.py

# Default: http://127.0.0.1:5010
# Custom port: PORT=5011 python run.py
```

#### Testing Strategy
**Important**: This project intentionally has **no formal test suite** to maintain MVP velocity.

**Manual Testing Workflow:**
1. Run `python verify_setup.py` to check basic health
2. Start the application with `python run.py`
3. Test changes by navigating through the web interface
4. Verify exports work by checking the `exports/` directory
5. For data exploration features, test in Jupyter notebooks

**When Making Changes:**
- Always test by running the application manually
- Verify all Flask routes still load without errors
- Check that Adobe Analytics API 1.4 service methods return expected data
- Ensure exports directory is writable and exports complete

#### Jupyter Notebook Workflow
```bash
# Start Jupyter
jupyter notebook

# Navigate to notebooks/ directory
# Each notebook is designed to be self-contained
# Test notebook changes by running all cells
```

#### Docker Build and Deployment
```bash
# Build and run locally
docker compose up -d --build

# View logs
docker compose logs -f

# Verify exports directory permissions
# Ensure: ./exports:/app/exports:rw in docker-compose.yml
```

#### Common Build/Runtime Issues
1. **Missing config.json**: Verify file exists and has required keys (org_id, client_id, secret, scope)
2. **Port already in use**: Try `PORT=5001 python run.py`
3. **Import errors**: Run `pip install -r requirements.txt`
4. **Docker export errors**: Check volume mount permissions (needs :rw flag)

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

### Adobe Analytics API (Library)

At this stage, a python library to work with the Adobe Analytics API 1.4 has not been selected. The [RShiny SDR](https://github.com/Brontojoris/rshiny-sdr) project relies on [RSiteCatalyst](https://randyzwitch.com/rsitecatalyst/).

Options are:

1. Use an equivalent python library
2. Use raw HTTP requests to the [Adobe Analytics API 1.4](https://developer.adobe.com/analytics-apis/docs/1.4/)

#### 1. Configuration & Authentication

**To be filled out**


#### 5. Typical Workflow

**To be filled out**

## Development Guidelines

### Core Principles

#### 1. MVP Velocity First
- **Primary Goal:** Generate functional, pragmatic code for the quickest path to a working prototype
- **Pragmatism Over Purity:** Choose simple solutions that reach functional milestones faster than architecturally perfect solutions
- **YAGNI Principle:** Only implement features required for the immediate MVP goal
- **Rapid Refactoring:** Expect and encourage frequent, small-scale refactoring - code is disposable and changeable

#### 2. Speed-Focused Technical Approach
- **Code Style:** Generally follow PEP 8, but don't waste time on minor stylistic tweaks that don't affect functionality
- **Testing:** Minimal/functional testing only - basic assertions to confirm immediate functionality works; skip comprehensive edge-case testing until post-MVP
- **Documentation:** Minimal inline comments focusing on *what* the code does and *why* specific choices were made
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

#### When Issues Arise
1. **To be filled out**

#### Common Pitfalls
1. **To be filled out**

### Troubleshooting Guide

#### Authentication Issues
**Symptom**: "Authentication failed" or 401 errors from API
**Possible Causes:**
- Missing or invalid `config.json` file

**Resolution Steps:**
1. Verify `config.json` exists in project root

### Code Quality Checklist

For every code suggestion, confirm:
- [ ] Compatible with Python 3.13+
- [ ] Uses existing project dependencies when possible
- [ ] Includes necessary imports
- [ ] Has minimal inline comments explaining non-obvious logic
- [ ] Follows simple, direct naming conventions
- [ ] Prioritizes functionality over perfection
- [ ] Suitable for Jupyter notebook workflow (if applicable)

### Documentation References

When providing guidance, reference these documentation files:
- **Getting Started:** [docs/getstarted.md](../docs/getstarted.md) - Authentication and initial setup
- **Main API Documentation:** [docs/main.md](../docs/main.md) - Core methods and workflows
- **Admin Class:** [docs/admin.md](../docs/admin.md) - Company and property management
- **Property Class:** [docs/property.md](../docs/property.md) - Property operations
- **Library Class:** [docs/library.md](../docs/library.md) - Publishing workflows
- **Translator Class:** [docs/translator.md](../docs/translator.md) - Cross-property element translation
- **Project Plan:** [docs/project_plan.md](../docs/project_plan.md) - Desktop application roadmap

### Operating Procedure

For every user request:
1. **Acknowledge the constraint** - Confirm adherence to MVP velocity and project constraints
2. **Generate code** - Provide the most direct, least complex code necessary
3. **Identify next step** - Explicitly state the most logical next functional step toward MVP
4. **Provide context** - Link to relevant documentation when appropriate

### Examples of Good Responses

TO BE FILLED OUT

---

## Quick Reference

TO BE FILLED OUT

---

## Additional Resources

For high-level project context and AI agent guidelines, see **[AGENTS.md](../AGENTS.md)** in the repository root.

For deployment procedures and production setup, see **[docs/deployment.md](../docs/deployment.md)**.

For getting started with authentication and API setup, see **[docs/getstarted.md](../docs/getstarted.md)**.

For post-mortem analysis of completed issues, see **[docs/autopsies/](../docs/autopsies/)**.

---

*Last updated: December 11, 2025*

