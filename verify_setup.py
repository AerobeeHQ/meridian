#!/usr/bin/env python3
"""
Verify Meridian setup
Checks: MERIDIAN_SECRETS_DIR, imports, app factory, directory structure
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
    """Check MERIDIAN_SECRETS_DIR is set and contains at least one valid client config."""
    import json
    from pathlib import Path

    print("Checking MERIDIAN_SECRETS_DIR...", end=" ")

    secrets_dir_raw = os.environ.get('MERIDIAN_SECRETS_DIR')
    if not secrets_dir_raw:
        print("FAIL - MERIDIAN_SECRETS_DIR is not set")
        print("  export MERIDIAN_SECRETS_DIR=/path/to/secrets/meridian")
        print("  Then place one JSON config per client: maxis.json, coles.json, etc.")
        return False

    secrets_dir = Path(secrets_dir_raw)
    if not secrets_dir.is_dir():
        print(f"FAIL - directory does not exist: {secrets_dir}")
        return False

    base_required = ['APP_TITLE', 'AW_REPORTSUITE_ID']
    valid_clients = []
    errors = []

    for config_file in sorted(secrets_dir.glob('*.json')):
        if config_file.name.startswith('_'):
            continue
        try:
            with open(config_file) as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            errors.append(f"{config_file.name}: {e}")
            continue

        api_version = config.get('API_VERSION', '2.0')
        if api_version == '2.0':
            required_keys = base_required + ['CLIENT_ID', 'CLIENT_SECRET', 'ORGANIZATION_ID', 'AW_USERNAME', 'AW_SECRET']
        else:
            required_keys = base_required + ['AW_USERNAME', 'AW_SECRET']

        missing = [k for k in required_keys if not config.get(k)]
        if missing:
            errors.append(f"{config_file.stem}: missing {', '.join(missing)}")
        else:
            valid_clients.append(f"{config_file.stem} (API {api_version})")

    if errors:
        for err in errors:
            print(f"\n  WARN - {err}", end="")
        print()

    if not valid_clients:
        print("FAIL - no valid client configs found")
        print(f"  Copy config.dist.json to {secrets_dir}/<client>.json and fill in credentials")
        return False

    print(f"OK ({', '.join(valid_clients)})")
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
    print("Meridian Setup Verification")
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

