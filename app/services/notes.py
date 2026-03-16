"""
Notes Service - JSON file-based storage for dimension notes.

Stores user-provided notes for each data dimension (props, evars, events, listvars).
Notes are stored as JSON files in a `notes/` directory, keyed by rsid_type_id.
"""

import json
import os
from datetime import datetime, timezone

# Notes directory path (relative to project root)
NOTES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'notes')


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
        Dict with 'content' and 'updated_at', or None if no note exists
    """
    filepath = _get_note_path(rsid, dimension_type, dimension_id)
    
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def set(rsid, dimension_type, dimension_id, content):
    """
    Save a note for a specific dimension.
    
    Args:
        rsid: Report suite ID
        dimension_type: Type of dimension (prop, evar, event, listvar)
        dimension_id: The dimension identifier
        content: The note text content
    
    Returns:
        Dict with 'content' and 'updated_at'
    """
    _ensure_notes_dir()
    filepath = _get_note_path(rsid, dimension_type, dimension_id)
    
    note_data = {
        'content': content,
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(note_data, f, ensure_ascii=False, indent=2)
    
    return note_data


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

