"""
Tests for AdobeAnalyticsService (app/services/adobe_analytics.py).

Covers pure logic that doesn't require network access:
- _generate_wsse_header: format and field presence
- _decode_raw_response: gzip, deflate/zlib, plain text, empty, invalid
- get_processing_rules: formatting logic (conditions, actions, else-actions)
- Endpoint rotation on Timeout / ConnectionError
"""
import base64
import gzip
import json
import zlib
import pytest
from unittest.mock import MagicMock, patch
import requests

from app.services.adobe_analytics import AdobeAnalyticsService


@pytest.fixture
def service():
    return AdobeAnalyticsService(username="user:company", secret="s3cr3t")


# ---------------------------------------------------------------------------
# _generate_wsse_header
# ---------------------------------------------------------------------------

class TestGenerateWsseHeader:
    def test_header_starts_with_username_token(self, service):
        header = service._generate_wsse_header()
        assert header.startswith("UsernameToken")

    def test_header_contains_username(self, service):
        header = service._generate_wsse_header()
        assert 'Username="user:company"' in header

    def test_header_contains_password_digest(self, service):
        header = service._generate_wsse_header()
        assert "PasswordDigest=" in header

    def test_header_contains_nonce(self, service):
        header = service._generate_wsse_header()
        assert "Nonce=" in header

    def test_header_contains_created(self, service):
        header = service._generate_wsse_header()
        assert "Created=" in header

    def test_nonce_is_valid_base64(self, service):
        header = service._generate_wsse_header()
        # Extract the Nonce value
        for part in header.split(", "):
            if part.startswith("Nonce="):
                nonce_val = part.split("=", 1)[1].strip('"')
                # Should not raise
                base64.b64decode(nonce_val)
                return
        pytest.fail("Nonce field not found in WSSE header")

    def test_password_digest_is_valid_base64(self, service):
        header = service._generate_wsse_header()
        for part in header.split(", "):
            if part.startswith("PasswordDigest="):
                digest_val = part.split("=", 1)[1].strip('"')
                base64.b64decode(digest_val)
                return
        pytest.fail("PasswordDigest not found in WSSE header")

    def test_each_call_produces_unique_nonce(self, service):
        h1 = service._generate_wsse_header()
        h2 = service._generate_wsse_header()
        # Extract nonce from each
        def extract_nonce(h):
            for part in h.split(", "):
                if part.startswith("Nonce="):
                    return part.split("=", 1)[1].strip('"')
        assert extract_nonce(h1) != extract_nonce(h2)


# ---------------------------------------------------------------------------
# _decode_raw_response
# ---------------------------------------------------------------------------

class TestDecodeRawResponse:
    def test_decodes_gzip_bytes(self, service):
        data = {"key": "value"}
        raw = gzip.compress(json.dumps(data).encode("utf-8"))
        result = service._decode_raw_response(raw)
        assert result == data

    def test_decodes_deflate_bytes(self, service):
        data = {"hello": "world"}
        raw = zlib.compress(json.dumps(data).encode("utf-8"))
        # Remove the zlib header (first 2 bytes) to get raw deflate
        raw_deflate = raw[2:]
        result = service._decode_raw_response(raw_deflate)
        assert result == data

    def test_decodes_plain_utf8_json(self, service):
        data = {"plain": True}
        raw = json.dumps(data).encode("utf-8")
        result = service._decode_raw_response(raw)
        assert result == data

    def test_decodes_string_input(self, service):
        data = {"str": "input"}
        result = service._decode_raw_response(json.dumps(data))
        assert result == data

    def test_returns_empty_dict_for_empty_bytes(self, service):
        result = service._decode_raw_response(b"")
        assert result == {}

    def test_returns_empty_dict_for_whitespace_bytes(self, service):
        result = service._decode_raw_response(b"   \n  ")
        assert result == {}

    def test_returns_empty_dict_for_non_json_text(self, service):
        result = service._decode_raw_response(b"not json at all")
        assert result == {}


# ---------------------------------------------------------------------------
# get_processing_rules — formatting logic
# ---------------------------------------------------------------------------

class TestGetProcessingRules:
    def _make_rule(self, title="Rule", rules=None, actions=None, else_actions=None, match_on="all"):
        return {
            "title": title,
            "rules": rules or ["condition A"],
            "matchOn": match_on,
            "actions": actions or ["set evar1 = 'foo'"],
            "elseActions": else_actions or [],
            "comment": "",
        }

    def _mock_service_response(self, rsid, raw_rules):
        """Build the full response shape that _make_request returns."""
        return [{"rsid": rsid, "processing_rules": raw_rules}]

    def test_formats_single_rule(self, service):
        raw = self._mock_service_response("rsid1", [self._make_rule()])
        with patch.object(service, "_make_request", return_value=raw):
            rules = service.get_processing_rules("rsid1")
        assert len(rules) == 1
        assert rules[0]["ruleNum"] == 1
        assert rules[0]["title"] == "Rule"

    def test_conditions_joined_with_newline(self, service):
        raw = self._mock_service_response(
            "rsid1", [self._make_rule(rules=["cond A", "cond B"])]
        )
        with patch.object(service, "_make_request", return_value=raw):
            rules = service.get_processing_rules("rsid1")
        assert rules[0]["rules"] == "cond A\ncond B"

    def test_actions_joined_with_newline(self, service):
        raw = self._mock_service_response(
            "rsid1", [self._make_rule(actions=["act1", "act2"])]
        )
        with patch.object(service, "_make_request", return_value=raw):
            rules = service.get_processing_rules("rsid1")
        assert rules[0]["actions"] == "act1\nact2"

    def test_else_actions_appended_with_separator(self, service):
        raw = self._mock_service_response(
            "rsid1",
            [self._make_rule(actions=["act1"], else_actions=["else1"])],
        )
        with patch.object(service, "_make_request", return_value=raw):
            rules = service.get_processing_rules("rsid1")
        assert "--- ELSE ---" in rules[0]["actions"]
        assert "else1" in rules[0]["actions"]

    def test_returns_empty_list_for_wrong_rsid(self, service):
        raw = [{"rsid": "other_rsid", "processing_rules": [self._make_rule()]}]
        with patch.object(service, "_make_request", return_value=raw):
            rules = service.get_processing_rules("rsid1")
        assert rules == []

    def test_returns_empty_list_when_response_not_list(self, service):
        with patch.object(service, "_make_request", return_value={"error": "oops"}):
            rules = service.get_processing_rules("rsid1")
        assert rules == []

    def test_rule_numbers_are_sequential(self, service):
        raw = self._mock_service_response(
            "rsid1", [self._make_rule("R1"), self._make_rule("R2"), self._make_rule("R3")]
        )
        with patch.object(service, "_make_request", return_value=raw):
            rules = service.get_processing_rules("rsid1")
        assert [r["ruleNum"] for r in rules] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Endpoint rotation
# ---------------------------------------------------------------------------

class TestEndpointRotation:
    def test_rotates_to_next_endpoint_on_timeout(self, service):
        """If first endpoint times out, the service tries the next one."""
        call_count = [0]

        def fake_post(url, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise requests.exceptions.Timeout("timed out")
            resp = MagicMock()
            resp.ok = True
            resp.status_code = 200
            resp.raise_for_status = lambda: None
            resp.json.return_value = {"report_suites": [{"rsid": "abc"}]}
            return resp

        with patch("app.services.adobe_analytics.requests.post", side_effect=fake_post):
            result = service.get_report_suites()

        assert call_count[0] == 2
        assert result == [{"rsid": "abc"}]

    def test_raises_after_all_endpoints_fail(self, service):
        with patch(
            "app.services.adobe_analytics.requests.post",
            side_effect=requests.exceptions.Timeout("always times out"),
        ):
            with pytest.raises(requests.exceptions.Timeout):
                service.get_report_suites()


# ---------------------------------------------------------------------------
# Simple API wrapper methods
# ---------------------------------------------------------------------------

class TestSimpleApiWrappers:
    def _ok_response(self, data):
        resp = MagicMock()
        resp.ok = True
        resp.raise_for_status = lambda: None
        resp.json.return_value = data
        return resp

    def test_get_props_extracts_props_array(self, service):
        data = [{"rsid": "r", "props": [{"id": "prop1"}]}]
        with patch("app.services.adobe_analytics.requests.post",
                   return_value=self._ok_response(data)):
            result = service.get_props("r")
        assert result == [{"id": "prop1"}]

    def test_get_props_returns_empty_on_empty_response(self, service):
        with patch("app.services.adobe_analytics.requests.post",
                   return_value=self._ok_response([])):
            result = service.get_props("r")
        assert result == []

    def test_get_evars_extracts_evars_array(self, service):
        data = [{"rsid": "r", "evars": [{"id": "evar1"}]}]
        with patch("app.services.adobe_analytics.requests.post",
                   return_value=self._ok_response(data)):
            result = service.get_evars("r")
        assert result == [{"id": "evar1"}]

    def test_get_evar_finds_by_id(self, service):
        data = [{"rsid": "r", "evars": [{"id": "evar1", "name": "Page Name"}, {"id": "evar2"}]}]
        with patch("app.services.adobe_analytics.requests.post",
                   return_value=self._ok_response(data)):
            result = service.get_evar("r", "evar1")
        assert result["name"] == "Page Name"

    def test_get_evar_strips_variables_prefix(self, service):
        data = [{"rsid": "r", "evars": [{"id": "evar3", "name": "Channel"}]}]
        with patch("app.services.adobe_analytics.requests.post",
                   return_value=self._ok_response(data)):
            result = service.get_evar("r", "variables/evar3")
        assert result["name"] == "Channel"

    def test_get_evar_returns_empty_dict_when_not_found(self, service):
        data = [{"rsid": "r", "evars": []}]
        with patch("app.services.adobe_analytics.requests.post",
                   return_value=self._ok_response(data)):
            result = service.get_evar("r", "evar99")
        assert result == {}

    def test_get_success_events_returns_list(self, service):
        data = [{"rsid": "r", "events": [{"id": "event1"}]}]
        with patch("app.services.adobe_analytics.requests.post",
                   return_value=self._ok_response(data)):
            result = service.get_success_events("r")
        assert result == [{"id": "event1"}]
