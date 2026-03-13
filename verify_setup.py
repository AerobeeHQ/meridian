#!/usr/bin/env python3
"""
Verify Codex setup
Checks: config.json, imports, app factory, directory structure
"""
import sys
import os


def check_python_version():
    """Check Python version is 3.10+"""
    print("Checking Python version...", end=" ")
    if sys.version_info < (3, 10):
        print(f"FAIL - Python 3.10+ required, got {sys.version}")
        return False
    print(f"OK ({sys.version_info.major}.{sys.version_info.minor})")
    return True


def check_config():
    """Check config.json exists and has required keys"""
    print("Checking config.json...", end=" ")
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    if not os.path.exists(config_path):
        print("FAIL - config.json not found")
        print("  Copy config.dist.json to config.json and fill in your credentials")
        return False

    import json
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"FAIL - Invalid JSON: {e}")
        return False

    # Check API version and validate appropriate credentials
    api_version = config.get('API_VERSION', '2.0')

    # Always required
    base_required = ['APP_TITLE', 'AW_REPORTSUITE_ID']

    if api_version == '2.0':
        # OAuth2 credentials required for API 2.0
        oauth_required = ['CLIENT_ID', 'CLIENT_SECRET', 'ORGANIZATION_ID']
        # WSSE credentials still needed for processing rules (not in 2.0 API)
        wsse_required = ['AW_USERNAME', 'AW_SECRET']
        required_keys = base_required + oauth_required + wsse_required
    else:
        # API 1.4 only needs WSSE
        required_keys = base_required + ['AW_USERNAME', 'AW_SECRET']

    missing = [k for k in required_keys if not config.get(k)]

    if missing:
        print(f"FAIL - Missing keys: {', '.join(missing)}")
        return False

    print(f"OK (API {api_version})")
    return True


def check_imports():
    """Check required packages can be imported"""
    print("Checking imports...", end=" ")

    # Core dependencies only (flask, requests)
    packages = ['flask', 'requests']
    missing = []

    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"FAIL - Missing packages: {', '.join(missing)}")
        print("  Run: uv sync")
        return False

    print("OK")
    return True


def check_app_factory():
    """Check Flask app can be created"""
    print("Checking app factory...", end=" ")

    try:
        from app import create_app
        app = create_app()
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL - {e}")
        return False


def check_directories():
    """Check and create required directories"""
    print("Checking directories...", end=" ")

    dirs = ['cache', 'exports']
    created = []

    for d in dirs:
        dir_path = os.path.join(os.path.dirname(__file__), d)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            created.append(d)

    if created:
        print(f"OK (created: {', '.join(created)})")
    else:
        print("OK")

    return True


def main():
    """Run all checks"""
    print("=" * 50)
    print("Codex Setup Verification")
    print("=" * 50)
    print()

    checks = [
        check_python_version,
        check_config,
        check_imports,
        check_directories,
        check_app_factory,
    ]

    results = []
    for check in checks:
        results.append(check())

    print()
    print("=" * 50)

    if all(results):
        print("All checks passed! Run 'python run.py' to start the app.")
        return 0
    else:
        print("Some checks failed. Please fix the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

