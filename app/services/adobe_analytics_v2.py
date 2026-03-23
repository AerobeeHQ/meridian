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
        Get list of report suites (via discovery endpoint)

        Uses the cached discovery response — no extra HTTP call is made
        once ``_get_discovery_data`` has been called at least once.

        Returns:
            List of report suite dictionaries with rsid and name
        """
        global_company_id = self._get_global_company_id()
        data = self._get_discovery_data()  # returns cached data; safe to call again

        report_suites = []
        for ims_org in data.get("imsOrgs", []):
            for company in ims_org.get("companies", []):
                if company.get("globalCompanyId") == global_company_id:
                    # Note: Discovery doesn't list all RSIDs, we might need
                    # to use a different approach or the reportSuites endpoint
                    # For now, return company info
                    report_suites.append({
                        "rsid": company.get("companyName", ""),
                        "company_name": company.get("companyName", ""),
                        "global_company_id": company.get("globalCompanyId", "")
                    })

        return report_suites

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

    def _transform_dimension_to_evar(self, dim: dict) -> dict:
        """Transform a 2.0 dimension to 1.4 eVar format"""
        dim_id = dim.get("id", "")
        # Extract evar number from "variables/evar1" -> "evar1"
        evar_id = dim_id.replace("variables/", "")
        
        # Extract status from reportable list (e.g., ['oberon'] -> 'oberon')
        reportable = dim.get("reportable", [])
        status = ", ".join(reportable) if reportable else ""

        return {
            "id": evar_id,
            "name": dim.get("name", ""),
            "status": status,
            "type": dim.get("type", "text string"),
            "expiration_type": dim.get("expirationType", ""),
            "allocation_type": dim.get("allocationModel", {}).get("name", ""),
            "description": dim.get("description", "")
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

    @staticmethod
    def _extract_number(s: str) -> int:
        """Extract numeric suffix from a string like 'prop1' -> 1"""
        match = re.search(r'(\d+)$', s)
        return int(match.group(1)) if match else 0

