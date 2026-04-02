"""
Adobe Analytics API 2.0 Service
Uses OAuth2 authentication via adobe_auth module
"""
import logging
import re
import statistics
from datetime import datetime, timedelta
from typing import Any, Optional

import requests

from app.services.adobe_auth import OAuth2Auth

logger = logging.getLogger(__name__)


class AdobeAnalyticsV2Service:
    """Service for interacting with Adobe Analytics API 2.0"""

    API_BASE = "https://analytics.adobe.io/api"

    # Discovery endpoint to get company ID (globalCompanyId)
    DISCOVERY_URL = "https://analytics.adobe.io/discovery/me"

    def __init__(self, auth_service: OAuth2Auth, client_id: str, org_id: str):
        """
        Initialize the Adobe Analytics 2.0 service

        Args:
            auth_service: OAuth2Auth instance for token management
            client_id: API client ID (x-api-key header)
            org_id: Organization ID (format: XXXXX@AdobeOrg)
        """
        self.auth_service = auth_service
        self.client_id = client_id
        self.org_id = org_id
        self._global_company_id: Optional[str] = None
        self._discovery_data: Optional[dict] = None
        self._suite_names: dict[str, str] = {}

    def _get_headers(self) -> dict:
        """Get headers required for API requests"""
        return {
            "Authorization": f"Bearer {self.auth_service.get_access_token()}",
            "x-api-key": self.client_id,
            "x-gw-ims-org-id": self.org_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _get_discovery_data(self) -> dict:
        """
        Fetch and cache the discovery endpoint response.

        Result is stored in ``_discovery_data`` so subsequent calls
        (including ``_get_global_company_id`` and ``get_report_suites``)
        share the same in-memory copy without making duplicate HTTP requests.
        """
        if self._discovery_data is not None:
            return self._discovery_data

        logger.info("Fetching discovery data from %s", self.DISCOVERY_URL)
        response = requests.get(
            self.DISCOVERY_URL,
            headers=self._get_headers()
        )

        if not response.ok:
            logger.error(
                "Discovery failed: %s %s - %s",
                response.status_code,
                response.reason,
                response.text
            )
            response.raise_for_status()

        self._discovery_data = response.json()
        return self._discovery_data

    def _get_global_company_id(self) -> str:
        """
        Get the global company ID via discovery endpoint

        The globalCompanyId is required for all API 2.0 requests.
        This is cached after first retrieval.
        """
        if self._global_company_id:
            return self._global_company_id

        data = self._get_discovery_data()
        # Response contains imsOrgs array, each with companies array
        # Find the company matching our org_id
        for ims_org in data.get("imsOrgs", []):
            if ims_org.get("imsOrgId") == self.org_id:
                companies = ims_org.get("companies", [])
                if companies:
                    self._global_company_id = companies[0].get("globalCompanyId")
                    logger.info("Global company ID: %s", self._global_company_id)
                    return self._global_company_id

        # Fallback: try first company from first org
        if data.get("imsOrgs"):
            companies = data["imsOrgs"][0].get("companies", [])
            if companies:
                self._global_company_id = companies[0].get("globalCompanyId")
                logger.warning(
                    "Using fallback global company ID: %s",
                    self._global_company_id
                )
                return self._global_company_id

        raise ValueError("Could not determine globalCompanyId from discovery endpoint")

    def get_experience_cloud_url(
        self, component_type: str, component_id: str, org_alias: Optional[str] = None
    ) -> Optional[str]:
        """
        Build a deep-link URL to the Adobe Experience Cloud Analytics UI.

        Args:
            component_type: ``"segments"`` or ``"calculatedMetrics"``.
            component_id:   The segment or calculated metric ID.
            org_alias:      The company alias that appears after ``@`` in
                            Experience Cloud URLs (e.g. ``"originenergy"``).
                            Comes from the ``EXPERIENCE_CLOUD_ORG`` config key.
                            If absent no URL is returned.

        Returns:
            A full URL string, or ``None`` when either identifier is missing.
        """
        if not org_alias:
            return None
        global_company_id = self._get_global_company_id()
        if not global_company_id:
            return None

        base = (
            f"https://experience.adobe.com/#/@{org_alias}"
            f"/so:{global_company_id}/analytics/spa"
        )
        return f"{base}/#/components/{component_type}/edit/{component_id}"

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict = None,
        json_data: dict = None
    ) -> Any:
        """
        Make a request to the Adobe Analytics 2.0 API

        Args:
            endpoint: API endpoint path (without base URL)
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            json_data: JSON body for POST requests

        Returns:
            JSON response from the API
        """
        global_company_id = self._get_global_company_id()
        url = f"{self.API_BASE}/{global_company_id}/{endpoint.lstrip('/')}"

        logger.debug(
            "Adobe API 2.0 request %s %s params=%s",
            method,
            endpoint,
            list(params.keys()) if params else []
        )

        response = requests.request(
            method=method,
            url=url,
            headers=self._get_headers(),
            params=params,
            json=json_data
        )

        if not response.ok:
            logger.error(
                "Adobe API 2.0 error: %s %s - %s",
                response.status_code,
                response.reason,
                response.text
            )
            response.raise_for_status()

        logger.debug(
            "Adobe API 2.0 response %s status=%s length=%s",
            endpoint,
            response.status_code,
            response.headers.get('Content-Length', 'unknown')
        )

        return response.json()

    def get_report_suites(self) -> list[dict]:
        """
        Get all report suites accessible to this service account.

        Uses the ``reportsuites/collections/suites`` API 2.0 endpoint, which
        returns both base and virtual report suites.  Results are sorted
        alphabetically by name.

        Returns:
            List of dicts with rsid, name, type, currency, and timezone fields.
        """
        results: list[dict] = []
        page = 0
        page_size = 100

        while True:
            data = self._make_request(
                "reportsuites/collections/suites",
                params={
                    "limit": page_size,
                    "page": page,
                },
            )
            content = data.get("content", [])
            if not isinstance(content, list):
                break

            for rs in content:
                results.append({
                    "rsid": rs.get("rsid", ""),
                    "name": rs.get("name", ""),
                    "type": rs.get("type", "base").capitalize(),
                    "currency": rs.get("currency", ""),
                    "timezone": rs.get("timezoneZoneInfo", ""),
                })

            total = data.get("totalElements", 0)
            if len(results) >= total or not content:
                break
            page += 1

        logger.debug("Found %s report suites", len(results))
        return sorted(results, key=lambda x: x.get("name", "").lower())

    def get_report_suite_name(self, rsid: str) -> str:
        """
        Get the friendly name of a report suite.

        Fetches one segment tied to the rsid with expansion=reportSuiteName,
        which is the cheapest API 2.0 call that returns this field.
        Result is cached per rsid on the service instance.

        Args:
            rsid: Report suite ID

        Returns:
            Friendly report suite name, or rsid if not found
        """
        if rsid in self._suite_names:
            return self._suite_names[rsid]

        try:
            result = self._make_request(
                "reportsuites/collections/suites",
                params={"rsids": rsid}
            )
            content = result.get("content", [])
            if content:
                name = content[0].get("name", rsid)
                self._suite_names[rsid] = name
                logger.info("Report suite name for %s: %s", rsid, name)
                return name
        except Exception:
            logger.warning("Could not fetch report suite name for %s", rsid)

        self._suite_names[rsid] = rsid
        return rsid

    def get_dimensions(self, rsid: str) -> list[dict]:
        """
        Get all dimensions for a report suite

        This returns both props (traffic variables) and eVars (conversion variables)
        mixed together. Use filter methods to separate them.

        Args:
            rsid: Report suite ID

        Returns:
            List of dimension objects
        """
        result = self._make_request(
            "dimensions",
            params={"rsid": rsid}
        )

        # API returns array directly
        if isinstance(result, list):
            return result
        return []

    def get_props(self, rsid: str) -> list[dict]:
        """
        Get traffic variables (props) for a report suite

        Props in the 2.0 API are dimensions with id starting with "variables/prop"

        Args:
            rsid: Report suite ID

        Returns:
            List of prop configurations transformed to match 1.4 API format
        """
        dimensions = self.get_dimensions(rsid)

        props = []
        for dim in dimensions:
            dim_id = dim.get("id", "")
            # Props have IDs like "variables/prop1", "variables/prop2", etc.
            if dim_id.startswith("variables/prop"):
                props.append(self._transform_dimension_to_prop(dim))

        # Sort by prop number
        props.sort(key=lambda x: self._extract_number(x.get("id", "")))
        logger.debug("Found %s props for %s", len(props), rsid)
        return props

    def get_evars(self, rsid: str) -> list[dict]:
        """
        Get conversion variables (eVars) for a report suite

        eVars in the 2.0 API are dimensions with id starting with "variables/evar"

        Args:
            rsid: Report suite ID

        Returns:
            List of eVar configurations transformed to match 1.4 API format
        """
        dimensions = self.get_dimensions(rsid)

        evars = []
        for dim in dimensions:
            dim_id = dim.get("id", "")
            # eVars have IDs like "variables/evar1", "variables/evar2", etc.
            if dim_id.startswith("variables/evar"):
                evars.append(self._transform_dimension_to_evar(dim))

        # Sort by evar number
        evars.sort(key=lambda x: self._extract_number(x.get("id", "")))
        logger.debug("Found %s eVars for %s", len(evars), rsid)
        return evars

    def get_metrics(self, rsid: str) -> list[dict]:
        """
        Get all metrics for a report suite

        Args:
            rsid: Report suite ID

        Returns:
            List of metric objects
        """
        result = self._make_request(
            "metrics",
            params={"rsid": rsid}
        )

        if isinstance(result, list):
            return result
        return []

    def get_success_events(self, rsid: str) -> list[dict]:
        """
        Get success events for a report suite

        Events in the 2.0 API are metrics with id starting with "metrics/event"

        Args:
            rsid: Report suite ID

        Returns:
            List of event configurations transformed to match 1.4 API format
        """
        metrics = self.get_metrics(rsid)

        events = []
        for metric in metrics:
            metric_id = metric.get("id", "")
            # Events have IDs like "metrics/event1", "metrics/event2", etc.
            if metric_id.startswith("metrics/event"):
                events.append(self._transform_metric_to_event(metric))

        # Sort by event number
        events.sort(key=lambda x: self._extract_number(x.get("id", "")))
        logger.debug("Found %s success events for %s", len(events), rsid)
        return events

    # -------------------------------------------------------------------------
    # Transform methods to convert 2.0 API responses to 1.4 format
    # -------------------------------------------------------------------------

    def _transform_dimension_to_prop(self, dim: dict) -> dict:
        """Transform a 2.0 dimension to 1.4 prop format"""
        dim_id = dim.get("id", "")
        # Extract prop number from "variables/prop1" -> "prop1"
        prop_id = dim_id.replace("variables/", "")
        
        # Extract status from reportable list (e.g., ['oberon'] -> 'oberon')
        reportable = dim.get("reportable", [])
        status = ", ".join(reportable) if reportable else ""

        return {
            "id": prop_id,
            "name": dim.get("name", ""),
            "status": status,
            "pathing_enabled": dim.get("pathingEnabled", False),
            "list_enabled": dim.get("listEnabled", False),
            "list_delimiter": dim.get("listDelimiter", ""),
            "description": dim.get("description", "")
        }

    @staticmethod
    def parse_description_metadata(description: str) -> dict:
        """Parse expiration and allocation from an API 2.0 description field.

        The API 2.0 embeds configuration metadata as structured text at the
        end of the description, e.g.:

            Expiration: Purchase.
            Allocation: Merchandising (Last)

        Returns a dict with keys ``expiration_type``, ``expiration_custom_days``
        and ``allocation_type`` (any may be empty strings).
        """
        result = {
            'expiration_type': '',
            'expiration_custom_days': '',
            'allocation_type': '',
        }
        if not description:
            return result

        # Match "Expiration: <value>." — value may include digits + text
        exp_match = re.search(r'Expiration:\s*(.+?)\.', description)
        if exp_match:
            raw = exp_match.group(1).strip()
            # Check for custom-day format, e.g. "30 Days"
            days_match = re.match(r'^(\d+)\s*[Dd]ays?$', raw)
            if days_match:
                result['expiration_custom_days'] = days_match.group(1)
                result['expiration_type'] = 'custom'
            else:
                # Map common labels to the canonical keys the template expects
                label_map = {
                    'hit': 'hit',
                    'visit': 'visit',
                    'day': 'day',
                    'week': 'week',
                    'month': 'month',
                    'quarter': 'quarter',
                    'year': 'year',
                    'purchase': 'purchase_event',
                    'purchase event': 'purchase_event',
                    'product view': 'product_view',
                    'never': 'never',
                }
                result['expiration_type'] = label_map.get(raw.lower(), raw)

        # Match "Allocation: <value>" (may or may not end with period)
        alloc_match = re.search(r'Allocation:\s*(.+?)\.?\s*$', description, re.MULTILINE)
        if alloc_match:
            result['allocation_type'] = alloc_match.group(1).strip()

        return result

    def _transform_dimension_to_evar(self, dim: dict) -> dict:
        """Transform a 2.0 dimension to 1.4 eVar format"""
        dim_id = dim.get("id", "")
        # Extract evar number from "variables/evar1" -> "evar1"
        evar_id = dim_id.replace("variables/", "")

        # Extract status from reportable list (e.g., ['oberon'] -> 'oberon')
        reportable = dim.get("reportable", [])
        status = ", ".join(reportable) if reportable else ""

        # Parse expiration & allocation from the description field — API 2.0
        # embeds these as structured text rather than separate fields.
        description = dim.get("description", "")
        parsed = self.parse_description_metadata(description)

        return {
            "id": evar_id,
            "name": dim.get("name", ""),
            "status": status,
            "type": dim.get("type", "text string"),
            "expiration_type": parsed['expiration_type'],
            "expiration_custom_days": parsed['expiration_custom_days'],
            "allocation_type": parsed['allocation_type'],
            "description": description
        }

    def _transform_metric_to_event(self, metric: dict) -> dict:
        """Transform a 2.0 metric to 1.4 event format"""
        metric_id = metric.get("id", "")
        # Extract event number from "metrics/event1" -> "event1"
        event_id = metric_id.replace("metrics/", "")

        return {
            "id": event_id,
            "name": metric.get("name", ""),
            "type": metric.get("type", ""),
            "serialization": metric.get("serialization", ""),
            "description": metric.get("description", "")
        }

    # -------------------------------------------------------------------------
    # Dimension Detail Methods
    # -------------------------------------------------------------------------

    def get_dimension(self, rsid: str, dimension_id: str) -> dict:
        """
        Get details for a single dimension

        Args:
            rsid: Report suite ID
            dimension_id: Dimension ID (e.g., 'variables/prop1' or 'prop1')

        Returns:
            Dimension configuration details
        """
        # Ensure dimension_id has 'variables/' prefix for matching
        if not dimension_id.startswith("variables/"):
            dimension_id = f"variables/{dimension_id}"

        # Get all dimensions and filter for the specific one
        # This is more reliable than the single dimension endpoint
        dimensions = self.get_dimensions(rsid)

        for dim in dimensions:
            if dim.get("id") == dimension_id:
                return dim

        # Not found
        return {}

    def get_metric(self, rsid: str, metric_id: str) -> dict:
        """
        Get details for a single metric/event

        Args:
            rsid: Report suite ID
            metric_id: Metric ID (e.g., 'metrics/event1' or 'event1')

        Returns:
            Metric configuration details
        """
        # Ensure metric_id has 'metrics/' prefix for matching
        if not metric_id.startswith("metrics/"):
            metric_id = f"metrics/{metric_id}"

        # Get all metrics and filter for the specific one
        metrics = self.get_metrics(rsid)

        for metric in metrics:
            if metric.get("id") == metric_id:
                return metric

        # Not found
        return {}

    def get_event_trend(
        self,
        rsid: str,
        event_id: str,
        days: int = 30
    ) -> dict:
        """
        Get daily trend data for an event (total occurrences per day)

        Args:
            rsid: Report suite ID
            event_id: Event ID (e.g., 'metrics/event1' or 'event1')
            days: Number of days to look back

        Returns:
            Dict with 'dates', 'values', and 'stats' (avg, median, max, min)
        """
        # Ensure event_id has 'metrics/' prefix
        if not event_id.startswith("metrics/"):
            event_id = f"metrics/{event_id}"

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Build report request for time-series data using the event as the metric
        request_body = {
            "rsid": rsid,
            "globalFilters": [
                {
                    "type": "dateRange",
                    "dateRange": f"{start_date.strftime('%Y-%m-%dT00:00:00')}/{end_date.strftime('%Y-%m-%dT23:59:59')}"
                }
            ],
            "metricContainer": {
                "metrics": [{"id": event_id}]
            },
            "dimension": "variables/daterangeday",
            "settings": {
                "dimensionSort": "asc",
                "limit": days + 1
            }
        }

        result = self._make_request("reports", method="POST", json_data=request_body)

        # Extract dates and values from response
        dates = []
        values = []

        for row in result.get("rows", []):
            # daterangeday returns dates like "Jan 1, 2024"
            date_str = row.get("value", "")
            dates.append(date_str)

            # Get the metric value (first metric in our request)
            row_data = row.get("data", [0])
            raw = row_data[0] if row_data else 0
            # The API can return strings ("N/A") for some metrics; coerce to float.
            value = raw if isinstance(raw, (int, float)) else 0
            values.append(value)

        # Calculate statistics
        stats = {}
        if values:
            stats = {
                "avg": round(sum(values) / len(values), 1),
                "median": round(statistics.median(values), 1),
                "max": max(values),
                "min": min(values)
            }

        return {"dates": dates, "values": values, "stats": stats}

    def get_metric_trend(
        self,
        rsid: str,
        metric_id: str,
        days: int = 30
    ) -> dict:
        """
        Get daily trend data for a calculated metric.

        Args:
            rsid: Report suite ID
            metric_id: Calculated metric ID (e.g., 'cm200000529_abc') — used as-is,
                       no 'metrics/' prefix added
            days: Number of days to look back

        Returns:
            Dict with 'dates', 'values', and 'stats' (avg, median, max, min)
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        request_body = {
            "rsid": rsid,
            "globalFilters": [
                {
                    "type": "dateRange",
                    "dateRange": f"{start_date.strftime('%Y-%m-%dT00:00:00')}/{end_date.strftime('%Y-%m-%dT23:59:59')}"
                }
            ],
            "metricContainer": {
                "metrics": [{"id": metric_id}]
            },
            "dimension": "variables/daterangeday",
            "settings": {
                "dimensionSort": "asc",
                "limit": days + 1
            }
        }

        result = self._make_request("reports", method="POST", json_data=request_body)

        dates = []
        values = []

        for row in result.get("rows", []):
            date_str = row.get("value", "")
            dates.append(date_str)
            row_data = row.get("data", [0])
            raw = row_data[0] if row_data else 0
            # The API can return strings ("N/A") for some metrics; coerce to float.
            value = raw if isinstance(raw, (int, float)) else 0
            values.append(value)

        stats = {}
        if values:
            stats = {
                "avg": round(sum(values) / len(values), 1),
                "median": round(statistics.median(values), 1),
                "max": max(values),
                "min": min(values)
            }

        return {"dates": dates, "values": values, "stats": stats}

    def get_top_items(
        self,
        rsid: str,
        dimension: str,
        metric: str = "occurrences",
        limit: int = 10,
        days: int = 30
    ) -> list[dict]:
        """
        Get top items for a dimension

        Args:
            rsid: Report suite ID
            dimension: Dimension ID (e.g., 'variables/prop1')
            metric: Metric to rank by ('occurrences' or 'instances')
            limit: Number of items to return
            days: Number of days to look back

        Returns:
            List of top items with value, count, and percentage
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Use POST /reports endpoint (more reliable permissions than GET /topItems)
        request_body = {
            "rsid": rsid,
            "globalFilters": [
                {
                    "type": "dateRange",
                    "dateRange": f"{start_date.strftime('%Y-%m-%dT00:00:00')}/{end_date.strftime('%Y-%m-%dT23:59:59')}"
                }
            ],
            "metricContainer": {
                "metrics": [{"id": f"metrics/{metric}"}]
            },
            "dimension": dimension,
            "settings": {
                "limit": limit,
                "page": 0
            }
        }

        result = self._make_request("reports", method="POST", json_data=request_body)

        # Transform response to simpler format with percentages
        items = []
        rows = result.get("rows", [])
        total = sum(row.get("data", [0])[0] for row in rows if row.get("data"))

        for row in rows:
            value = row.get("value", "")
            count = row.get("data", [0])[0] if row.get("data") else 0
            percentage = (count / total * 100) if total > 0 else 0
            items.append({
                "value": value,
                "count": count,
                "percentage": round(percentage, 1)
            })

        return items

    def get_dimension_trend(
        self,
        rsid: str,
        dimension: str,
        metric: str = "occurrences",
        days: int = 30
    ) -> dict:
        """
        Get daily trend data for a dimension (total occurrences per day)

        Args:
            rsid: Report suite ID
            dimension: Dimension ID (e.g., 'variables/prop1')
            metric: Metric to use ('occurrences' or 'instances')
            days: Number of days to look back

        Returns:
            Dict with 'dates', 'values', and 'stats' (avg, median, max, min)
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Build report request for time-series data
        request_body = {
            "rsid": rsid,
            "globalFilters": [
                {
                    "type": "dateRange",
                    "dateRange": f"{start_date.strftime('%Y-%m-%dT00:00:00')}/{end_date.strftime('%Y-%m-%dT23:59:59')}"
                }
            ],
            "metricContainer": {
                "metrics": [{"id": f"metrics/{metric}"}]
            },
            "dimension": "variables/daterangeday",
            "settings": {
                "dimensionSort": "asc",
                "limit": days + 1
            }
        }

        result = self._make_request("reports", method="POST", json_data=request_body)

        # Extract dates and values from response
        dates = []
        values = []

        for row in result.get("rows", []):
            # daterangeday returns dates like "Jan 1, 2024"
            date_str = row.get("value", "")
            dates.append(date_str)

            # Get the metric value (first metric in our request)
            row_data = row.get("data", [0])
            value = row_data[0] if row_data else 0
            values.append(value)

        # Calculate statistics
        stats = {}
        if values:
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            if numeric_values:
                stats = {
                    "avg": round(sum(numeric_values) / len(numeric_values), 1),
                    "median": round(statistics.median(numeric_values), 1),
                    "max": max(numeric_values),
                    "min": min(numeric_values)
                }

        return {"dates": dates, "values": values, "stats": stats}

    def get_segment(self, segment_id: str) -> dict:
        """
        Get full detail for a single segment.

        Args:
            segment_id: Segment ID (e.g. 's200000529_615bafc93a56e92d9dd2eaa0')

        Returns:
            Segment dict with all expanded fields, or empty dict if not found.
        """
        try:
            return self._make_request(
                f"segments/{segment_id}",
                params={"expansion": "ownerFullName,modified,tags,definition,compatibility"},
            )
        except Exception:
            logger.warning("Could not fetch segment %s", segment_id)
            return {}

    def get_calculated_metric(self, cm_id: str) -> dict:
        """
        Get full detail for a single calculated metric.

        Args:
            cm_id: Calculated metric ID (e.g. 'cm200000529_...')

        Returns:
            Calculated metric dict with all expanded fields, or empty dict.
        """
        try:
            return self._make_request(
                f"calculatedmetrics/{cm_id}",
                params={"expansion": "ownerFullName,modified,tags,definition"},
            )
        except Exception:
            logger.warning("Could not fetch calculated metric %s", cm_id)
            return {}

    def get_calculated_metrics(self, rsid: str) -> list[dict]:
        """
        Get all calculated metrics for a report suite (all pages).

        Uses includeType=all so company-level calculated metrics (which have no
        owner RSID binding) are included alongside RSID-specific ones.

        Args:
            rsid: Report suite ID

        Returns:
            List of calculated metric dicts with id, name, description, type,
            polarity, precision, owner, modified, and tags fields.
        """
        results: list[dict] = []
        page = 0
        page_size = 1000

        while True:
            data = self._make_request(
                "calculatedmetrics",
                params={
                    "rsids": rsid,
                    "includeType": "all",
                    "expansion": "ownerFullName,modified,tags,definition",
                    "limit": page_size,
                    "page": page,
                    "sortProperty": "name",
                    "sortDirection": "ASC",
                },
            )

            content = data.get("content", [])
            if not isinstance(content, list):
                break

            for cm in content:
                owner_obj = cm.get("owner") or {}
                tags_list = cm.get("tags") or []
                tag_names = ", ".join(
                    t.get("name", "") for t in tags_list if t.get("name")
                )
                results.append({
                    "id": cm.get("id", ""),
                    "name": cm.get("name", ""),
                    "description": cm.get("description", ""),
                    "type": cm.get("type", ""),
                    "polarity": cm.get("polarity", ""),
                    "precision": cm.get("precision", ""),
                    "owner": owner_obj.get("name") or owner_obj.get("login", ""),
                    "modified": (cm.get("modified") or "")[:10],
                    "tags": tag_names,
                    "definition": cm.get("definition"),
                })

            total = data.get("totalElements", 0)
            if len(results) >= total or not content:
                break
            page += 1

        logger.debug("Found %s calculated metrics for %s", len(results), rsid)
        return results

    def get_segments(self, rsid: str) -> list[dict]:
        """
        Get all segments for a report suite (all pages).

        Fetches segments tied to ``rsid``, paging through the API until all
        results are collected.  Each segment is normalised to a flat dict so
        the route layer can use it directly without further processing.

        Args:
            rsid: Report suite ID

        Returns:
            List of segment dicts with id, name, description, owner,
            modified, and tags fields.
        """
        segments: list[dict] = []
        page = 0
        page_size = 1000  # maximum allowed by the API

        while True:
            result = self._make_request(
                "segments",
                params={
                    "rsids": rsid,
                    "includeType": "all",
                    "expansion": "ownerFullName,modified,tags,definition",
                    "limit": page_size,
                    "page": page,
                    "sortProperty": "name",
                    "sortDirection": "ASC",
                },
            )

            # Response is a paginated envelope: {"content": [...], "totalElements": N, ...}
            content = result.get("content", [])
            if not isinstance(content, list):
                break

            for seg in content:
                owner_obj = seg.get("owner") or {}
                tags_list = seg.get("tags") or []
                tag_names = ", ".join(
                    t.get("name", "") for t in tags_list if t.get("name")
                )
                segments.append({
                    "id": seg.get("id", ""),
                    "name": seg.get("name", ""),
                    "description": seg.get("description", ""),
                    "owner": owner_obj.get("name") or owner_obj.get("login", ""),
                    "modified": (seg.get("modified") or "")[:10],  # keep date only
                    "tags": tag_names,
                    "definition": seg.get("definition"),
                })

            total = result.get("totalElements", 0)
            if len(segments) >= total or not content:
                break
            page += 1

        logger.debug("Found %s segments for %s", len(segments), rsid)
        return segments

    @staticmethod
    def _extract_number(s: str) -> int:
        """Extract numeric suffix from a string like 'prop1' -> 1"""
        match = re.search(r'(\d+)$', s)
        return int(match.group(1)) if match else 0

