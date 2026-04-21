"""
Tests for OAuth2Auth (app/services/adobe_auth.py).

Covers pure in-memory logic — no real HTTP calls:
- is_token_valid when no token set
- is_token_valid with fresh vs expired token
- get_access_token returns cached token when still valid
- get_access_token fetches new token when expired
- clear_token resets state
- Scope handling (list, comma-string, None → defaults)
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest

from app.services.adobe_auth import OAuth2Auth


@pytest.fixture
def auth():
    return OAuth2Auth(client_id="client123", client_secret="secret456")


# ---------------------------------------------------------------------------
# Scope parsing
# ---------------------------------------------------------------------------

class TestScopeParsing:
    def test_list_scopes_stored_as_is(self):
        a = OAuth2Auth("id", "secret", scopes=["openid", "AdobeID"])
        assert a.scopes == ["openid", "AdobeID"]

    def test_comma_string_scopes_split(self):
        a = OAuth2Auth("id", "secret", scopes="openid, AdobeID, extra.scope")
        assert "openid" in a.scopes
        assert "AdobeID" in a.scopes
        assert "extra.scope" in a.scopes

    def test_none_scopes_uses_defaults(self):
        a = OAuth2Auth("id", "secret", scopes=None)
        assert len(a.scopes) > 0
        assert "openid" in a.scopes


# ---------------------------------------------------------------------------
# is_token_valid
# ---------------------------------------------------------------------------

class TestIsTokenValid:
    def test_false_when_no_token(self, auth):
        assert auth.is_token_valid is False

    def test_false_when_token_but_no_expiry(self, auth):
        auth._access_token = "tok"
        auth._token_expires_at = None
        assert auth.is_token_valid is False

    def test_true_when_token_not_expired(self, auth):
        auth._access_token = "tok"
        auth._token_expires_at = datetime.now() + timedelta(hours=1)
        assert auth.is_token_valid is True

    def test_false_when_token_expired(self, auth):
        auth._access_token = "tok"
        auth._token_expires_at = datetime.now() - timedelta(seconds=1)
        assert auth.is_token_valid is False


# ---------------------------------------------------------------------------
# clear_token
# ---------------------------------------------------------------------------

class TestClearToken:
    def test_clear_token_resets_access_token(self, auth):
        auth._access_token = "some_token"
        auth._token_expires_at = datetime.now() + timedelta(hours=1)
        auth.clear_token()
        assert auth._access_token is None

    def test_clear_token_resets_expiry(self, auth):
        auth._token_expires_at = datetime.now() + timedelta(hours=1)
        auth.clear_token()
        assert auth._token_expires_at is None

    def test_is_token_valid_false_after_clear(self, auth):
        auth._access_token = "tok"
        auth._token_expires_at = datetime.now() + timedelta(hours=1)
        auth.clear_token()
        assert auth.is_token_valid is False


# ---------------------------------------------------------------------------
# get_access_token — caching behaviour
# ---------------------------------------------------------------------------

class TestGetAccessToken:
    def _mock_fetch(self, auth, token="fresh_token", expires_in=3600):
        """Patch _fetch_token to return a known token."""
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        auth._fetch_token = MagicMock(return_value=(token, expires_at))

    def test_calls_fetch_on_first_call(self, auth):
        self._mock_fetch(auth)
        token = auth.get_access_token()
        auth._fetch_token.assert_called_once()
        assert token == "fresh_token"

    def test_returns_cached_token_without_fetch(self, auth):
        auth._access_token = "cached"
        auth._token_expires_at = datetime.now() + timedelta(hours=2)
        self._mock_fetch(auth, token="new_token")
        result = auth.get_access_token()
        auth._fetch_token.assert_not_called()
        assert result == "cached"

    def test_refreshes_token_when_within_5_min_buffer(self, auth):
        """Token expiring in 3 minutes should trigger a refresh."""
        auth._access_token = "near_expiry"
        auth._token_expires_at = datetime.now() + timedelta(minutes=3)
        self._mock_fetch(auth, token="refreshed")
        result = auth.get_access_token()
        auth._fetch_token.assert_called_once()
        assert result == "refreshed"

    def test_refreshes_expired_token(self, auth):
        auth._access_token = "old"
        auth._token_expires_at = datetime.now() - timedelta(minutes=1)
        self._mock_fetch(auth, token="new")
        result = auth.get_access_token()
        auth._fetch_token.assert_called_once()
        assert result == "new"


# ---------------------------------------------------------------------------
# _fetch_token — HTTP interaction (mocked)
# ---------------------------------------------------------------------------

class TestFetchToken:
    def _make_response(self, token="tok", expires_in=86399):
        resp = MagicMock()
        resp.ok = True
        resp.raise_for_status = lambda: None
        resp.json.return_value = {"access_token": token, "expires_in": expires_in}
        return resp

    def test_fetch_token_posts_to_ims_endpoint(self, auth):
        with patch("app.services.adobe_auth.requests.post",
                   return_value=self._make_response()) as mock_post:
            auth._fetch_token()
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "adobelogin.com" in call_url

    def test_fetch_token_sends_client_credentials(self, auth):
        with patch("app.services.adobe_auth.requests.post",
                   return_value=self._make_response()) as mock_post:
            auth._fetch_token()
        payload = mock_post.call_args[1]["data"]
        assert payload["grant_type"] == "client_credentials"
        assert payload["client_id"] == "client123"
        assert payload["client_secret"] == "secret456"

    def test_fetch_token_returns_token_and_expiry(self, auth):
        with patch("app.services.adobe_auth.requests.post",
                   return_value=self._make_response(token="abc123", expires_in=7200)):
            token, expiry = auth._fetch_token()
        assert token == "abc123"
        assert expiry > datetime.now() + timedelta(hours=1)

    def test_fetch_token_raises_on_http_error(self, auth):
        import requests as req_lib

        resp = MagicMock()
        resp.ok = False
        resp.status_code = 401
        resp.reason = "Unauthorized"
        resp.text = "invalid client"
        resp.raise_for_status.side_effect = req_lib.HTTPError("401")

        with patch("app.services.adobe_auth.requests.post", return_value=resp):
            with pytest.raises(req_lib.HTTPError):
                auth._fetch_token()
