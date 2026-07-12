"""
Config loader for Meridian multisite.

Scans MERIDIAN_SECRETS_DIR for per-client JSON configuration files and returns
them as a dict keyed by client slug (the filename stem).

Convention:
    $MERIDIAN_SECRETS_DIR/maxis.json   → clients['maxis']
    $MERIDIAN_SECRETS_DIR/coles.json   → clients['coles']

Files whose names start with '_' are reserved for future app-level settings
and are silently skipped.

Usage:
    from app.services.config_loader import load_clients
    clients = load_clients()   # raises RuntimeError if MERIDIAN_SECRETS_DIR unset
"""
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Keys that must be present for a client config to be considered valid.
REQUIRED_KEYS = {'AW_REPORTSUITE_ID', 'API_VERSION'}


def get_secrets_dir() -> Path:
    """Return the secrets directory from the MERIDIAN_SECRETS_DIR env var.

    Raises:
        RuntimeError: If the env var is missing or the directory does not exist.
    """
    raw = os.environ.get('MERIDIAN_SECRETS_DIR')
    if not raw:
        raise RuntimeError(
            "MERIDIAN_SECRETS_DIR is not set. "
            "Point it to a directory containing per-client JSON config files.\n"
            "Example: export MERIDIAN_SECRETS_DIR=/Users/joris/secrets/meridian"
        )
    path = Path(raw)
    if not path.is_dir():
        raise RuntimeError(
            f"MERIDIAN_SECRETS_DIR does not exist or is not a directory: {path}"
        )
    return path


def load_clients() -> dict[str, dict[str, Any]]:
    """Load all client configurations from MERIDIAN_SECRETS_DIR.

    Returns:
        Dict mapping client slug → config dict, sorted alphabetically.

    Raises:
        RuntimeError: If MERIDIAN_SECRETS_DIR is unset, the directory is missing,
                      or no valid client configs are found.
    """
    secrets_dir = get_secrets_dir()
    clients: dict[str, dict[str, Any]] = {}

    for config_file in sorted(secrets_dir.glob('*.json')):
        if config_file.name.startswith('_'):
            logger.debug("Skipping reserved config file: %s", config_file.name)
            continue

        client_slug = config_file.stem
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            logger.warning("Could not load client config '%s': %s — skipping.", config_file.name, exc)
            continue

        missing = REQUIRED_KEYS - config.keys()
        if missing:
            logger.warning(
                "Client config '%s' is missing required keys %s — skipping.",
                client_slug, sorted(missing),
            )
            continue

        clients[client_slug] = config
        logger.info("Loaded client: %s  (rsid: %s)", client_slug, config.get('AW_REPORTSUITE_ID'))

    if not clients:
        raise RuntimeError(
            f"No valid client configs found in {secrets_dir}. "
            "Copy config.dist.json to $MERIDIAN_SECRETS_DIR/<client-name>.json "
            "and fill in the credentials."
        )

    return clients
