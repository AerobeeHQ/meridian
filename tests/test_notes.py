"""
Tests for the notes service (app/services/notes.py).

Covers:
- get / set / delete note CRUD
- Path sanitization (directory traversal prevention)
- get_empty_note structure
- Schema evolution (missing fields filled from empty note)
- Tags CRUD: get_tags / add_tag / delete_tag
- generate_expiry_notes for each dimension type
"""
import json
import os
import pytest

import app.services.notes as notes_module
from app.services.notes import (
    _resolve_notes_dir,
    get_empty_note,
    get,
    set as notes_set,
    delete,
    get_tags,
    add_tag,
    delete_tag,
    generate_expiry_notes,
    SQUAD_OPTIONS,
    PLATFORM_OPTIONS,
)


@pytest.fixture(autouse=True)
def isolated_notes_dir(tmp_path, monkeypatch):
    """Redirect NOTES_DIR to a fresh temp directory for every test."""
    monkeypatch.setattr(notes_module, "NOTES_DIR", str(tmp_path))
    yield tmp_path


# ---------------------------------------------------------------------------
# _resolve_notes_dir
# ---------------------------------------------------------------------------

class TestResolveNotesDir:
    def test_uses_secrets_dir_when_env_is_set(self, monkeypatch, tmp_path):
        monkeypatch.setenv('CODEX_SECRETS_DIR', str(tmp_path))
        result = _resolve_notes_dir()
        assert result == os.path.join(str(tmp_path), 'notes')

    def test_falls_back_to_project_root_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv('CODEX_SECRETS_DIR', raising=False)
        result = _resolve_notes_dir()
        assert result.endswith(os.sep + 'notes')
        assert 'CODEX_SECRETS_DIR' not in result


# ---------------------------------------------------------------------------
# get_empty_note
# ---------------------------------------------------------------------------

class TestGetEmptyNote:
    def test_returns_all_required_fields(self):
        note = get_empty_note()
        required = [
            "plain_description", "technical_definition", "expiry_notes",
            "platform_availability", "platform_notes", "web_equivalent",
            "app_equivalent", "use_cases", "typical_questions",
            "squad_owners", "last_verified", "updated_at",
        ]
        for field in required:
            assert field in note, f"Missing field: {field}"

    def test_squad_owners_is_empty_list(self):
        assert get_empty_note()["squad_owners"] == []

    def test_returns_independent_copies(self):
        a = get_empty_note()
        b = get_empty_note()
        a["plain_description"] = "mutated"
        assert b["plain_description"] == ""


# ---------------------------------------------------------------------------
# get / set / delete
# ---------------------------------------------------------------------------

class TestNoteCRUD:
    def test_get_returns_empty_note_when_no_file_exists(self):
        note = get("rsid1", "evar", "evar1")
        assert note == get_empty_note()

    def test_set_creates_file(self, tmp_path):
        notes_set("rsid1", "evar", "evar1", {"plain_description": "Page name"})
        filename = "rsid1_evar_evar1.json"
        assert (tmp_path / filename).exists()

    def test_set_then_get_round_trips(self):
        data = {"plain_description": "Product", "squad_owners": ["Shop"]}
        notes_set("rsid1", "evar", "evar5", data)
        result = get("rsid1", "evar", "evar5")
        assert result["plain_description"] == "Product"
        assert result["squad_owners"] == ["Shop"]

    def test_set_adds_updated_at(self):
        result = notes_set("rsid1", "evar", "evar1", {})
        assert result["updated_at"] != ""

    def test_get_fills_missing_fields(self, tmp_path):
        """Schema evolution: saved note missing a field gets default from empty note."""
        filepath = tmp_path / "rsid1_evar_evar1.json"
        with open(filepath, "w") as f:
            json.dump({"plain_description": "old note"}, f)
        note = get("rsid1", "evar", "evar1")
        # All fields from get_empty_note must be present
        for key in get_empty_note():
            assert key in note

    def test_get_with_corrupt_file_returns_empty_note(self, tmp_path):
        filepath = tmp_path / "rsid1_evar_evar1.json"
        filepath.write_text("{not valid json")
        note = get("rsid1", "evar", "evar1")
        assert note == get_empty_note()

    def test_delete_existing_note_returns_true(self):
        notes_set("rsid1", "evar", "evar1", {})
        deleted = delete("rsid1", "evar", "evar1")
        assert deleted is True

    def test_delete_removes_file(self, tmp_path):
        notes_set("rsid1", "evar", "evar1", {})
        delete("rsid1", "evar", "evar1")
        assert not (tmp_path / "rsid1_evar_evar1.json").exists()

    def test_delete_nonexistent_returns_false(self):
        result = delete("rsid1", "evar", "evar99")
        assert result is False

    def test_different_dimension_types_are_isolated(self):
        notes_set("rsid1", "evar", "evar1", {"plain_description": "eVar note"})
        notes_set("rsid1", "prop", "evar1", {"plain_description": "prop note"})
        assert get("rsid1", "evar", "evar1")["plain_description"] == "eVar note"
        assert get("rsid1", "prop", "evar1")["plain_description"] == "prop note"


# ---------------------------------------------------------------------------
# Path sanitization
# ---------------------------------------------------------------------------

class TestPathSanitization:
    def test_forward_slashes_replaced_in_rsid(self, tmp_path):
        notes_set("rsid/with/slashes", "evar", "evar1", {})
        saved_files = list(tmp_path.iterdir())
        # No actual subdirectories should have been created
        assert all(f.is_file() for f in saved_files)

    def test_backslashes_replaced(self, tmp_path):
        notes_set(r"rsid\evil", "evar", "evar1", {})
        saved_files = list(tmp_path.iterdir())
        assert all(f.is_file() for f in saved_files)

    def test_dot_dot_in_dimension_id_is_neutralised(self, tmp_path):
        """Ensure ../.. style IDs cannot escape the notes directory."""
        notes_set("rsid1", "evar", "../../etc/passwd", {})
        saved_files = list(tmp_path.iterdir())
        assert all(f.is_file() for f in saved_files)


# ---------------------------------------------------------------------------
# Tags CRUD
# ---------------------------------------------------------------------------

class TestTagsCRUD:
    def test_get_tags_returns_squad_options_when_no_file(self):
        tags = get_tags()
        assert tags == list(SQUAD_OPTIONS)

    def test_add_tag_appends_new_tag(self):
        tags = add_tag("NewTeam")
        assert "NewTeam" in tags

    def test_add_tag_persists(self):
        add_tag("Persist")
        assert "Persist" in get_tags()

    def test_add_tag_strips_whitespace(self):
        tags = add_tag("  SpacedTag  ")
        assert "SpacedTag" in tags

    def test_add_tag_raises_on_empty_name(self):
        with pytest.raises(ValueError, match="empty"):
            add_tag("   ")

    def test_add_tag_raises_on_duplicate(self):
        add_tag("Dup")
        with pytest.raises(ValueError, match="already exists"):
            add_tag("Dup")

    def test_delete_tag_removes_tag(self):
        add_tag("ToRemove")
        remaining = delete_tag("ToRemove")
        assert "ToRemove" not in remaining

    def test_delete_tag_raises_when_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            delete_tag("GhostTag")

    def test_get_tags_with_corrupt_file_falls_back(self, tmp_path):
        (tmp_path / "_tags.json").write_text("{bad json")
        tags = get_tags()
        assert tags == list(SQUAD_OPTIONS)


# ---------------------------------------------------------------------------
# generate_expiry_notes
# ---------------------------------------------------------------------------

class TestGenerateExpiryNotes:
    def test_prop_returns_fixed_message(self):
        result = generate_expiry_notes({}, "prop")
        assert "Props do not have expiration" in result

    def test_event_returns_fixed_message(self):
        result = generate_expiry_notes({}, "event")
        assert "do not expire" in result

    def test_evar_with_custom_days(self):
        dimension = {"expirationType": "visit", "expirationCustomDays": 30}
        result = generate_expiry_notes(dimension, "evar")
        assert "30" in result
        assert "visit" in result

    def test_evar_without_custom_days(self):
        dimension = {"expirationType": "hit"}
        result = generate_expiry_notes(dimension, "evar")
        assert "hit" in result

    def test_evar_no_expiration_set(self):
        result = generate_expiry_notes({}, "evar")
        assert "not configured" in result.lower()

    def test_listvar_same_as_evar(self):
        dimension = {"expirationType": "pageView"}
        result = generate_expiry_notes(dimension, "listvar")
        assert "pageView" in result

    def test_unknown_type_returns_empty_string(self):
        result = generate_expiry_notes({}, "unknown")
        assert result == ""
