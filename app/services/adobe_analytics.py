"""
Adobe Analytics API 1.4 Service
Uses WSSE authentication and raw HTTP requests
"""
import base64
import json
import gzip
import hashlib
import logging
import secrets
import zlib
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import requests
from flask import current_app


logger = logging.getLogger(__name__)


class AdobeAnalyticsService:
    """Service for interacting with Adobe Analytics API 1.4"""

    API_ENDPOINTS = [
        "https://api.omniture.com/admin/1.4/rest/",
        "https://api2.omniture.com/admin/1.4/rest/",
        "https://api3.omniture.com/admin/1.4/rest/",
        "https://api4.omniture.com/admin/1.4/rest/",
    ]

    # Minimum read timeout for authenticated API requests.
    # Adobe's API can take several seconds to respond even after the TCP
    # connection is established. The configured request_timeout is used as the
    # *connect* timeout (for fast failover during endpoint rotation); the read
    # timeout is always at least this value so slow-but-reachable endpoints
    # are not rejected prematurely.
    _MIN_READ_TIMEOUT = 30.0

    def __init__(self, username: str, secret: str, request_timeout: float | tuple[float, float] = 10.0):
        """
        Initialize the Adobe Analytics service

        Args:
            username: WSSE username (format: username:company)
            secret: WSSE shared secret
            request_timeout: Connect timeout in seconds for API 1.4 HTTP requests.
                             Used for connection attempts only; the read timeout is
                             always at least _MIN_READ_TIMEOUT seconds so slow
                             responses are not rejected prematurely.
                             A (connect, read) tuple is also accepted to override both.
        """
        self.username = username
        self.secret = secret
        self.request_timeout = request_timeout
        self._active_endpoint_index = 0  # index into API_ENDPOINTS; advances on timeout
        self._discovered_endpoint: str | None = None  # set by discover_endpoint()

    def _generate_wsse_header(self) -> str:
        """
        Generate WSSE authentication header

        The WSSE header format is:
        X-WSSE: UsernameToken Username="...", PasswordDigest="...", Nonce="...", Created="..."

        PasswordDigest = Base64(SHA1(Nonce + Created + Secret))
        """
        # Generate nonce (random bytes)
        nonce = secrets.token_bytes(16)
        nonce_base64 = base64.b64encode(nonce).decode('utf-8')

        # Generate timestamp in ISO 8601 format
        created = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        # Create password digest: Base64(SHA1(Nonce + Created + Secret))
        digest_input = nonce + created.encode('utf-8') + self.secret.encode('utf-8')
        sha1_hash = hashlib.sha1(digest_input).digest()
        password_digest = base64.b64encode(sha1_hash).decode('utf-8')

        # Build the X-WSSE header value
        wsse_header = (
            f'UsernameToken Username="{self.username}", '
            f'PasswordDigest="{password_digest}", '
            f'Nonce="{nonce_base64}", '
            f'Created="{created}"'
        )

        return wsse_header

    def discover_endpoint(self) -> None:
        """Discover and cache the correct API endpoint for this service's company.

        Calls ``Company.GetEndpoint`` without authentication — this is a public
        lookup that returns the company-specific API host (e.g.
        ``https://api3.omniture.com/admin/1.4/rest/``).  This mirrors the
        behaviour of the RSiteCatalyst R library, which always resolves the
        endpoint before making authenticated calls.

        The discovered endpoint is stored in ``self._discovered_endpoint`` and
        used by ``_make_request`` as the first endpoint to try, bypassing the
        round-robin rotation for the common case where the correct host is known.

        Failures are logged and silently ignored — the service falls back to the
        default endpoint rotation if discovery does not succeed.
        """
        if not self.username or ':' not in self.username:
            return
        company = self.username.split(':', 1)[1]
        try:
            url = f"{self.API_ENDPOINTS[0]}?method=Company.GetEndpoint"
            response = requests.post(url, json={"company": company}, timeout=10.0)
            response.raise_for_status()
            # Response is a JSON-encoded string: "\"https://api3.omniture.com/...\""
            try:
                endpoint = response.json()
            except Exception:
                endpoint = response.text.strip().strip('"').replace('\\', '')
            if isinstance(endpoint, str) and endpoint.startswith('http'):
                if not endpoint.endswith('/'):
                    endpoint += '/'
                parsed = urlparse(endpoint)
                valid = (
                    parsed.scheme == 'https'
                    and isinstance(parsed.hostname, str)
                    and (parsed.hostname == 'omniture.com' or parsed.hostname.endswith('.omniture.com'))
                    and parsed.path.startswith('/admin/1.4/rest/')
                )
                if valid:
                    logger.info("Discovered API 1.4 endpoint for company '%s': %s", company, endpoint)
                    self._discovered_endpoint = endpoint
                else:
                    logger.warning(
                        "Company.GetEndpoint returned an unexpected URL for '%s': %r; ignoring",
                        company, endpoint,
                    )
            else:
                logger.warning("Unexpected Company.GetEndpoint response for '%s': %r", company, endpoint)
        except Exception as exc:
            logger.warning(
                "Company.GetEndpoint discovery failed for '%s' (%s); will use default endpoint rotation",
                company, exc,
            )

    def _compute_timeout(self) -> tuple[float, float]:
        """Return the (connect_timeout, read_timeout) pair for API requests.

        If ``request_timeout`` is already a tuple it is returned unchanged.
        Otherwise the configured value is used as the *connect* timeout and the
        read timeout is set to ``max(request_timeout, _MIN_READ_TIMEOUT)`` so
        that slow-but-reachable endpoints are not rejected prematurely.
        """
        if isinstance(self.request_timeout, tuple):
            return self.request_timeout
        read = max(self.request_timeout, self._MIN_READ_TIMEOUT)
        return (self.request_timeout, read)

    def _make_request(self, method: str, params: dict = None) -> Any:
        """
        Make a request to the Adobe Analytics API, rotating through fallback
        endpoints when the primary host is unresponsive.

        If ``discover_endpoint()`` has been called and succeeded, the discovered
        endpoint is tried first before falling back to the default rotation.

        Args:
            method: API method name (e.g., "Company.GetReportSuites")
            params: Request parameters

        Returns:
            JSON response from the API
        """
        payload = params or {}
        timeout = self._compute_timeout()

        # Build the ordered list of endpoints to try.
        # Discovered endpoint (if any) goes first; the rest follow in rotation order.
        if self._discovered_endpoint:
            others = [e for e in self.API_ENDPOINTS if e != self._discovered_endpoint]
            endpoints_to_try = [self._discovered_endpoint] + others
        else:
            n = len(self.API_ENDPOINTS)
            endpoints_to_try = [
                self.API_ENDPOINTS[(self._active_endpoint_index + i) % n]
                for i in range(n)
            ]

        last_exc: Exception = None

        for attempt, endpoint in enumerate(endpoints_to_try):
            url = f"{endpoint}?method={method}"
            # Fresh WSSE header per attempt — the token is time-stamped
            headers = {
                'X-WSSE': self._generate_wsse_header(),
                'Content-Type': 'application/json',
            }
            logger.debug("Adobe API request %s via %s (attempt %d)", method, endpoint, attempt + 1)

            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                logger.debug(
                    "Adobe API response %s status=%s encoding=%s",
                    method,
                    response.status_code,
                    response.headers.get('Content-Encoding', 'unknown'),
                )
                data = response.json()
                # Update the active rotation index when a non-discovered endpoint succeeds
                if not self._discovered_endpoint and endpoint in self.API_ENDPOINTS:
                    idx = self.API_ENDPOINTS.index(endpoint)
                    if idx != self._active_endpoint_index:
                        logger.info("API 1.4 endpoint rotated to %s after %d attempt(s)", endpoint, attempt + 1)
                        self._active_endpoint_index = idx
                return data
            except requests.exceptions.ContentDecodingError:
                logger.warning("Adobe API response %s had broken compression; retrying with manual decoding", method)
                return self._fetch_with_manual_decoding(url, payload, headers, timeout)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                logger.warning("API 1.4 endpoint %s unavailable (%s); trying next", endpoint, exc)
                if endpoint == self._discovered_endpoint:
                    logger.info(
                        "Discovered endpoint %s failed; clearing so subsequent requests use default rotation",
                        endpoint,
                    )
                    self._discovered_endpoint = None
                last_exc = exc

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("All Adobe Analytics API 1.4 endpoints failed without a captured exception.")

    def _fetch_with_manual_decoding(self, url: str, params: dict, headers: dict, timeout=None) -> Any:
        """Retry the request while handling compression manually"""
        retry_headers = dict(headers)
        retry_headers['Accept-Encoding'] = 'identity'
        logger.debug("Manual retry for %s with Accept-Encoding=identity", url)

        response = requests.post(
            url,
            headers=retry_headers,
            json=params,
            stream=True,
            timeout=timeout if timeout is not None else self._compute_timeout(),
        )
        response.raise_for_status()

        raw_data = response.raw.read(decode_content=False)
        logger.debug("Manual decode received %s bytes", len(raw_data))
        return self._decode_raw_response(raw_data)

    def _decode_raw_response(self, raw_data: bytes | str) -> Any:
        """Decode raw response bytes into JSON"""
        if isinstance(raw_data, str):
            logger.debug("Decoding already-text response")
            return json.loads(raw_data)

        if raw_data[:2] == b'\x1f\x8b':
            try:
                decoded = gzip.decompress(raw_data)
                logger.debug("Decoded response via gzip")
                return json.loads(decoded.decode('utf-8'))
            except Exception:
                logger.exception("Gzip decompression failed, trying other strategies")

        try:
            decompressed = zlib.decompress(raw_data, -zlib.MAX_WBITS)
            logger.debug("Decoded response via zlib")
            return json.loads(decompressed.decode('utf-8'))
        except Exception:
            logger.debug("Zlib decompression failed; falling back to plain text decoding")

        try:
            text = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            text = raw_data.decode('latin-1')

        if not text.strip():
            logger.debug("Manual decode yielded empty payload")
            return {}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Manual decode produced non-JSON payload; returning empty dict")
            return {}

    def get_report_suites(self) -> list[dict]:
        """
        Get list of report suites

        Returns:
            List of report suite dictionaries
        """
        result = self._make_request("Company.GetReportSuites")
        return result.get('report_suites', [])

    def get_props(self, rsid: str) -> list[dict]:
        """
        Get traffic variables (props) for a report suite

        Args:
            rsid: Report suite ID

        Returns:
            List of prop configurations
        """
        result = self._make_request(
            "ReportSuite.GetProps",
            {"rsid_list": [rsid]}
        )

        # API returns array of report suites, we want the first one's props
        if result and len(result) > 0:
            return result[0].get('props', [])
        return []

    def get_evars(self, rsid: str) -> list[dict]:
        """
        Get conversion variables (eVars) for a report suite

        Args:
            rsid: Report suite ID

        Returns:
            List of eVar configurations
        """
        result = self._make_request(
            "ReportSuite.GetEvars",
            {"rsid_list": [rsid]}
        )

        if result and len(result) > 0:
            return result[0].get('evars', [])
        return []

    def get_evar(self, rsid: str, evar_id: str) -> dict:
        """
        Get configuration for a single eVar

        Args:
            rsid: Report suite ID
            evar_id: eVar ID (e.g., 'evar1' or 'variables/evar1')

        Returns:
            eVar configuration dict with allocation, expiration, and merchandising settings
        """
        # Normalize evar_id to just the evar number (e.g., 'evar1')
        evar_id = evar_id.replace('variables/', '')

        # Get all evars and find the matching one
        evars = self.get_evars(rsid)
        for evar in evars:
            if evar.get('id') == evar_id:
                return evar

        return {}

    def get_success_events(self, rsid: str) -> list[dict]:
        """
        Get success events for a report suite

        Args:
            rsid: Report suite ID

        Returns:
            List of event configurations
        """
        result = self._make_request(
            "ReportSuite.GetEvents",
            {"rsid_list": [rsid]}
        )

        events = []
        if result and len(result) > 0:
            events = result[0].get('events', [])
        logger.debug("Fetched %s success events for %s", len(events), rsid)
        return events

    def get_list_variables(self, rsid: str) -> list[dict]:
        """
        Get list variables for a report suite

        Args:
            rsid: Report suite ID

        Returns:
            List of list variable configurations
        """
        result = self._make_request(
            "ReportSuite.GetListVariables",
            {"rsid_list": [rsid]}
        )

        if result and len(result) > 0:
            return result[0].get('list_variables', [])
        return []

    def get_processing_rules(self, rsid: str) -> list[dict]:
        """
        Get processing rules for a report suite

        Args:
            rsid: Report suite ID

        Returns:
            List of processing rule configurations
        """
        result = self._make_request(
            "ReportSuite.ViewProcessingRules",
            {"rsid_list": [rsid]}
        )

        if not isinstance(result, list):
            logger.warning("Unexpected processing rules response for %s", rsid)
            return []

        suite_entry = next((item for item in result if item.get('rsid') == rsid), {})
        rules = suite_entry.get('processing_rules', []) or []

        formatted_rules = []
        for idx, rule in enumerate(rules, start=1):
            condition_text = '\n'.join(rule.get('rules') or [])
            actions = rule.get('actions') or []
            else_actions = rule.get('elseActions') or []
            actions_text = '\n'.join(actions)
            if else_actions:
                else_text = '\n'.join(else_actions)
                separator = '\n--- ELSE ---\n' if actions_text else '--- ELSE ---\n'
                actions_text = f"{actions_text}{separator}{else_text}"

            formatted_rules.append({
                'ruleNum': idx,
                'title': rule.get('title', ''),
                'rules': condition_text,
                'matchOn': rule.get('matchOn', ''),
                'actions': actions_text,
                'comment': rule.get('comment', '')
            })

        logger.debug("Fetched %s processing rules for %s", len(formatted_rules), rsid)
        return formatted_rules

    def get_marketing_channels(self, rsid: str) -> list[dict]:
        """
        Get marketing channels for a report suite

        Args:
            rsid: Report suite ID

        Returns:
            List of marketing channel configurations
        """
        result = self._make_request(
            "ReportSuite.GetMarketingChannels",
            {"rsid_list": [rsid]}
        )

        if result and len(result) > 0:
            return result[0].get('marketing_channels', [])
        return []

    def get_marketing_channel_rules(self, rsid: str) -> list[dict]:
        """
        Get marketing channel rules for a report suite

        Args:
            rsid: Report suite ID

        Returns:
            List of marketing channel rule configurations
        """
        result = self._make_request(
            "ReportSuite.GetMarketingChannelRules",
            {"rsid_list": [rsid]}
        )

        if result and len(result) > 0:
            return result[0].get('marketing_channel_rules', [])
        return []


def get_api_service_v14() -> AdobeAnalyticsService:
    """
    Get API 1.4 service (used for processing rules which aren't in 2.0).

    Stored on the app instance for the same reason as ``get_api_service``.

    Returns:
        AdobeAnalyticsService configured for API 1.4
    """
    app = current_app._get_current_object()

    if not hasattr(app, 'meridian_api_service_v14'):
        request_timeout = current_app.config.get('API_V14_TIMEOUT', 25.0)
        logger.info("Initializing API 1.4 service with timeout=%s", request_timeout)
        app.meridian_api_service_v14 = AdobeAnalyticsService(
            username=current_app.config['AW_USERNAME'],
            secret=current_app.config['AW_SECRET'],
            request_timeout=request_timeout,
        )
    return app.meridian_api_service_v14