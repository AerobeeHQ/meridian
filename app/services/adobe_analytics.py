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

import requests


logger = logging.getLogger(__name__)


class AdobeAnalyticsService:
    """Service for interacting with Adobe Analytics API 1.4"""

    API_ENDPOINT = "https://api.omniture.com/admin/1.4/rest/"

    def __init__(self, username: str, secret: str):
        """
        Initialize the Adobe Analytics service

        Args:
            username: WSSE username (format: username:company)
            secret: WSSE shared secret
        """
        self.username = username
        self.secret = secret

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

    def _make_request(self, method: str, params: dict = None) -> Any:
        """
        Make a request to the Adobe Analytics API

        Args:
            method: API method name (e.g., "Company.GetReportSuites")
            params: Request parameters

        Returns:
            JSON response from the API
        """
        headers = {
            'X-WSSE': self._generate_wsse_header(),
            'Content-Type': 'application/json',
        }

        url = f"{self.API_ENDPOINT}?method={method}"
        payload = params or {}
        logger.debug(
            "Adobe API request %s payload keys=%s",
            method,
            list(payload.keys())
        )

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            logger.debug(
                "Adobe API response %s status=%s encoding=%s length=%s",
                method,
                response.status_code,
                response.headers.get('Content-Encoding', 'unknown'),
                response.headers.get('Content-Length', 'unknown')
            )
            data = response.json()
            logger.debug(
                "Adobe API response %s parsed type=%s",
                method,
                type(data).__name__
            )
            return data
        except requests.exceptions.ContentDecodingError:
            logger.warning(
                "Adobe API response %s had broken compression; retrying with manual decoding",
                method
            )
            return self._fetch_with_manual_decoding(url, payload, headers)

    def _fetch_with_manual_decoding(self, url: str, params: dict, headers: dict) -> Any:
        """Retry the request while handling compression manually"""
        retry_headers = dict(headers)
        retry_headers['Accept-Encoding'] = 'identity'
        logger.debug("Manual retry for %s with Accept-Encoding=identity", url)

        response = requests.post(
            url,
            headers=retry_headers,
            json=params,
            stream=True
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
