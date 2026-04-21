"""
Notes Service - JSON file-based storage for dimension notes.

Stores user-provided notes for each data dimension (props, evars, events, listvars).
Notes are stored as JSON files in a `notes/` directory, keyed by rsid_type_id.
"""

import json
import os
from datetime import datetime, timezone

def _resolve_notes_dir() -> str:
    """Resolve the notes storage directory.

    Prefers ``$CODEX_SECRETS_DIR/notes`` so that notes survive container
    redeploys (the secrets volume is mounted outside the image).  Falls back
    to ``{project_root}/notes`` for local development where the env var is
    not set.
    """
    secrets_dir = os.environ.get('CODEX_SECRETS_DIR')
    if secrets_dir:
        return os.path.join(secrets_dir, 'notes')
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'notes')


# Notes directory — resolved once at module import time.
# Tests override this via ``monkeypatch.setattr(notes_module, "NOTES_DIR", ...)``.
NOTES_DIR = _resolve_notes_dir()

# Squad options for Journey Squad Owner field
SQUAD_OPTIONS = [
    "Shop", "Inspire", "Checkout", "Trolley", "Loyalty", 
    "Perso", "Finance", "Search", "Instore", "Platform", "All Squads"
]

# Platform availability options
PLATFORM_OPTIONS = [
    {"value": "", "label": "Not Set"},
    {"value": "web_only", "label": "Web Only"},
    {"value": "app_only", "label": "App Only"},
    {"value": "both", "label": "Both Web and App"}
]

# Default empty note structure
def get_empty_note():
    """Return the default empty note structure."""
    return {
        "plain_description": "",
        "technical_definition": "",
        "expiry_notes": "",
        "platform_availability": "",
        "platform_notes": "",
        "web_equivalent": "",
        "app_equivalent": "",
        "use_cases": "",
        "typical_questions": "",
        "squad_owners": [],
        "last_verified": "",
        "updated_at": ""
    }


def _ensure_notes_dir():
    """Create notes directory if it doesn't exist."""
    if not os.path.exists(NOTES_DIR):
        os.makedirs(NOTES_DIR)


def _get_note_path(rsid, dimension_type, dimension_id):
    """
    Build the file path for a note.
    
    Args:
        rsid: Report suite ID
        dimension_type: Type of dimension (prop, evar, event, listvar)
        dimension_id: The dimension identifier (e.g., 'prop1', 'evar5', 'event10')
    
    Returns:
        Full path to the note JSON file
    """
    # Sanitize inputs to prevent directory traversal
    safe_rsid = rsid.replace('/', '_').replace('\\', '_')
    safe_type = dimension_type.replace('/', '_').replace('\\', '_')
    safe_id = dimension_id.replace('/', '_').replace('\\', '_')
    
    filename = f"{safe_rsid}_{safe_type}_{safe_id}.json"
    return os.path.join(NOTES_DIR, filename)


def get(rsid, dimension_type, dimension_id):
    """
    Retrieve a note for a specific dimension.
    
    Args:
        rsid: Report suite ID
        dimension_type: Type of dimension (prop, evar, event, listvar)
        dimension_id: The dimension identifier
    
    Returns:
        Dict with all note fields, or empty note structure if no note exists
    """
    filepath = _get_note_path(rsid, dimension_type, dimension_id)
    
    if not os.path.exists(filepath):
        return get_empty_note()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            saved_note = json.load(f)
            # Merge with empty note to ensure all fields exist (handles schema evolution)
            note = get_empty_note()
            note.update(saved_note)
            return note
    except (json.JSONDecodeError, IOError):
        return get_empty_note()


def set(rsid, dimension_type, dimension_id, note_data):
    """
    Save a note for a specific dimension.
    
    Args:
        rsid: Report suite ID
        dimension_type: Type of dimension (prop, evar, event, listvar)
        dimension_id: The dimension identifier
        note_data: Dict containing note fields
    
    Returns:
        Dict with saved note data including updated_at
    """
    _ensure_notes_dir()
    filepath = _get_note_path(rsid, dimension_type, dimension_id)
    
    # Start with empty structure and update with provided data
    note = get_empty_note()
    note.update(note_data)
    note['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(note, f, ensure_ascii=False, indent=2)
    
    return note


def delete(rsid, dimension_type, dimension_id):
    """
    Delete a note for a specific dimension.
    
    Args:
        rsid: Report suite ID
        dimension_type: Type of dimension (prop, evar, event, listvar)
        dimension_id: The dimension identifier
    
    Returns:
        True if deleted, False if note didn't exist
    """
    filepath = _get_note_path(rsid, dimension_type, dimension_id)
    
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


# ---------------------------------------------------------------------------
# Tag-library management
# ---------------------------------------------------------------------------

_TAGS_FILENAME = '_tags.json'


def _get_tags_path() -> str:
    """Return the path to the global tags configuration file."""
    return os.path.join(NOTES_DIR, _TAGS_FILENAME)


def get_tags() -> list[str]:
    """Return the current list of available tags.

    Reads from ``notes/_tags.json`` if it exists; otherwise falls back to
    the built-in ``SQUAD_OPTIONS`` list so existing deployments see their
    previous chips without any migration step.

    Returns:
        Ordered list of tag name strings.
    """
    tags_path = _get_tags_path()
    if not os.path.exists(tags_path):
        return list(SQUAD_OPTIONS)
    try:
        with open(tags_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return [str(t) for t in data]
    except (json.JSONDecodeError, IOError) as exc:
        # If the tags file is unreadable or malformed, fall back to the built-in defaults.
        print(f"Warning: failed to load tags from {tags_path!r}: {exc}. Falling back to default SQUAD_OPTIONS.")
    return list(SQUAD_OPTIONS)


def _save_tags(tags: list[str]) -> list[str]:
    """Persist *tags* to disk and return the same list."""
    _ensure_notes_dir()
    with open(_get_tags_path(), 'w', encoding='utf-8') as fh:
        json.dump(tags, fh, ensure_ascii=False, indent=2)
    return tags


def add_tag(name: str) -> list[str]:
    """Add *name* to the tag library.

    Args:
        name: Tag label to add. Leading/trailing whitespace is stripped.

    Returns:
        Updated list of tags (includes the new entry).

    Raises:
        ValueError: If *name* is empty or already present in the list.
    """
    name = name.strip()
    if not name:
        raise ValueError("Tag name cannot be empty")
    tags = get_tags()
    if name in tags:
        raise ValueError(f"Tag '{name}' already exists")
    tags.append(name)
    return _save_tags(tags)


def delete_tag(name: str) -> list[str]:
    """Remove *name* from the tag library.

    Does **not** modify existing notes that already reference the deleted tag;
    their ``squad_owners`` arrays retain the value.

    Args:
        name: Tag label to remove.

    Returns:
        Updated list of tags (excludes the removed entry).

    Raises:
        ValueError: If *name* is not present in the current list.
    """
    tags = get_tags()
    if name not in tags:
        raise ValueError(f"Tag '{name}' not found")
    return _save_tags([t for t in tags if t != name])


def generate_expiry_notes(dimension, dimension_type):
    """
    Generate default expiry notes from dimension API data.
    
    Args:
        dimension: The dimension data from Adobe Analytics API
        dimension_type: Type of dimension (prop, evar, event, listvar)
    
    Returns:
        String with auto-generated expiry description
    """
    if dimension_type == 'prop':
        return "Props do not have expiration - values are associated with the hit in which they are set."
    
    if dimension_type == 'event':
        return "Events are recorded at the time of the hit and do not expire."
    
    if dimension_type in ('evar', 'listvar'):
        expiry_type = dimension.get('expirationType') or dimension.get('expiration_type', '')
        custom_days = dimension.get('expirationCustomDays') or dimension.get('expiration_custom_days', '')
        
        if expiry_type:
            if custom_days:
                return f"Expires after {custom_days} days ({expiry_type})."
            return f"Expiration type: {expiry_type}."
        return "Expiration not configured."
    
    return ""

