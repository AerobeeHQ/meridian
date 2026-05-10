"""
Tests for AdobeAnalyticsV2Service (app/services/adobe_analytics_v2.py).

Covers pure logic that doesn't require network access:
- _extract_tag_names: typical tags, empty/missing tags, entries without names
- get_dimensions: request params include expansion=tags
- get_metrics: request params include expansion=tags
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.adobe_analytics_v2 import AdobeAnalyticsV2Service


@pytest.fixture
def service():
    """Return a service instance with mocked auth and stubbed company ID."""
    auth = MagicMock()
    auth.get_access_token.return_value = "test-token"
    svc = AdobeAnalyticsV2Service(
        auth_service=auth,
        client_id="test-client-id",
        org_id="TEST_ORG@AdobeOrg",
    )
    # Pre-set company ID so _get_global_company_id() never hits the network
    svc._global_company_id = "testco"
    return svc


def _get_passed_params(mock_call):
    """Extract the 'params' dict from a mock call regardless of how it was passed."""
    args, kwargs = mock_call
    return kwargs.get("params") or (args[1] if len(args) > 1 else {})


# ---------------------------------------------------------------------------
# _extract_tag_names
# ---------------------------------------------------------------------------

class TestExtractTagNames:
    def test_returns_comma_separated_names(self):
        obj = {"tags": [{"name": "Alpha"}, {"name": "Beta"}]}
        result = AdobeAnalyticsV2Service._extract_tag_names(obj)
        assert result == "Alpha, Beta"

    def test_returns_single_tag_name(self):
        obj = {"tags": [{"name": "Only"}]}
        result = AdobeAnalyticsV2Service._extract_tag_names(obj)
        assert result == "Only"

    def test_returns_empty_string_when_tags_absent(self):
        obj = {"id": "variables/prop1"}
        result = AdobeAnalyticsV2Service._extract_tag_names(obj)
        assert result == ""

    def test_returns_empty_string_when_tags_is_none(self):
        obj = {"tags": None}
        result = AdobeAnalyticsV2Service._extract_tag_names(obj)
        assert result == ""

    def test_returns_empty_string_when_tags_is_empty_list(self):
        obj = {"tags": []}
        result = AdobeAnalyticsV2Service._extract_tag_names(obj)
        assert result == ""

    def test_skips_entries_without_name_key(self):
        obj = {"tags": [{"id": 1}, {"name": "Valid"}, {}]}
        result = AdobeAnalyticsV2Service._extract_tag_names(obj)
        assert result == "Valid"

    def test_skips_entries_with_empty_name(self):
        obj = {"tags": [{"name": ""}, {"name": "Real"}]}
        result = AdobeAnalyticsV2Service._extract_tag_names(obj)
        assert result == "Real"


# ---------------------------------------------------------------------------
# get_dimensions — expansion=tags in request params
# ---------------------------------------------------------------------------

class TestGetDimensions:
    def test_request_includes_expansion_tags(self, service):
        """get_dimensions must pass expansion=tags to the API."""
        fake_dims = [{"id": "variables/prop1", "name": "Page"}]
        with patch.object(service, "_make_request", return_value=fake_dims) as mock_req:
            service.get_dimensions("myrsid")

        mock_req.assert_called_once()
        params = _get_passed_params(mock_req.call_args)
        assert params.get("expansion") == "tags"

    def test_request_includes_rsid(self, service):
        """get_dimensions must pass the rsid query parameter."""
        with patch.object(service, "_make_request", return_value=[]) as mock_req:
            service.get_dimensions("suite123")

        params = _get_passed_params(mock_req.call_args)
        assert params.get("rsid") == "suite123"

    def test_returns_list_from_api(self, service):
        fake_dims = [{"id": "variables/evar1"}, {"id": "variables/prop1"}]
        with patch.object(service, "_make_request", return_value=fake_dims):
            result = service.get_dimensions("rsid")
        assert result == fake_dims

    def test_returns_empty_list_when_api_returns_dict(self, service):
        with patch.object(service, "_make_request", return_value={"error": "oops"}):
            result = service.get_dimensions("rsid")
        assert result == []


# ---------------------------------------------------------------------------
# get_metrics — expansion=tags in request params
# ---------------------------------------------------------------------------

class TestGetMetrics:
    def test_request_includes_expansion_tags(self, service):
        """get_metrics must pass expansion=tags to the API."""
        with patch.object(service, "_make_request", return_value=[]) as mock_req:
            service.get_metrics("myrsid")

        mock_req.assert_called_once()
        params = _get_passed_params(mock_req.call_args)
        assert params.get("expansion") == "tags"

    def test_request_includes_rsid(self, service):
        """get_metrics must pass the rsid query parameter."""
        with patch.object(service, "_make_request", return_value=[]) as mock_req:
            service.get_metrics("suite456")

        params = _get_passed_params(mock_req.call_args)
        assert params.get("rsid") == "suite456"

    def test_returns_list_from_api(self, service):
        fake_metrics = [{"id": "metrics/event1"}, {"id": "metrics/event2"}]
        with patch.object(service, "_make_request", return_value=fake_metrics):
            result = service.get_metrics("rsid")
        assert result == fake_metrics

    def test_returns_empty_list_when_api_returns_dict(self, service):
        with patch.object(service, "_make_request", return_value={"error": "oops"}):
            result = service.get_metrics("rsid")
        assert result == []


# ---------------------------------------------------------------------------
# Integration: tags flow through transform methods
# ---------------------------------------------------------------------------

class TestTagsInTransforms:
    def test_prop_transform_includes_tag_names(self, service):
        """Tags from the API object reach the transformed prop dict."""
        dim = {
            "id": "variables/prop1",
            "name": "Page",
            "tags": [{"name": "Squad A"}, {"name": "Core"}],
        }
        prop = service._transform_dimension_to_prop(dim)
        assert prop["tags"] == "Squad A, Core"

    def test_prop_transform_empty_tags(self, service):
        dim = {"id": "variables/prop1", "name": "Page", "tags": []}
        prop = service._transform_dimension_to_prop(dim)
        assert prop["tags"] == ""

    def test_evar_transform_includes_tag_names(self, service):
        dim = {
            "id": "variables/evar1",
            "name": "Channel",
            "tags": [{"name": "Marketing"}],
        }
        evar = service._transform_dimension_to_evar(dim)
        assert evar["tags"] == "Marketing"

    def test_evar_transform_no_tags_field(self, service):
        dim = {"id": "variables/evar1", "name": "Channel"}
        evar = service._transform_dimension_to_evar(dim)
        assert evar["tags"] == ""

    def test_event_transform_includes_tag_names(self, service):
        metric = {
            "id": "metrics/event1",
            "name": "Purchase",
            "tags": [{"name": "Revenue"}, {"name": "Checkout"}],
        }
        event = service._transform_metric_to_event(metric)
        assert event["tags"] == "Revenue, Checkout"

    def test_event_transform_no_tags_field(self, service):
        metric = {"id": "metrics/event1", "name": "Purchase"}
        event = service._transform_metric_to_event(metric)
        assert event["tags"] == ""
