"""
Adobe Experience Platform Tags (Reactor) API client.

Uses the Reactor /search API to find all property resources (rules, rule
components, data elements, extensions) that reference a given Analytics
dimension string (e.g. 'eVar1', 'prop5', 'event3').

This approach is not scoped to the production library and matches custom
code actions as well as structured setVariables actions, giving a more
complete picture than walking the library graph.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from app.services.adobe_auth import OAuth2Auth

logger = logging.getLogger(__name__)

REACTOR_BASE_URL = "https://reactor.adobe.io"


class AdobeLaunchService:
    """
    Client for the Adobe Experience Platform Reactor (Tags) API.

    Searches the property for Analytics dimension references using the
    /search endpoint and returns display-ready dicts for Codex detail pages.
    """

    def __init__(self, auth_service: OAuth2Auth, org_id: str):
        self.auth = auth_service
        self.org_id = org_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.auth.get_access_token()}",
            "X-Api-Key": self.auth.client_id,
            "x-gw-ims-org-id": self.org_id,
            "Accept": "application/vnd.api+json;revision=1",
        }

    def _get_all_pages(self, url: str, params: dict = None) -> list:
        """Fetch every page from a paginated Reactor API endpoint."""
        results = []
        while url:
            resp = requests.get(url, headers=self._headers(), params=params)
            if not resp.ok:
                logger.error(
                    "Reactor API error %s %s — response: %s",
                    resp.status_code, resp.reason, resp.text[:500],
                )
            resp.raise_for_status()
            body = resp.json()
            results.extend(body.get("data", []))
            url = body.get("links", {}).get("next")
            params = None  # Subsequent pages use the full URL from links.next
        return results

    def post_raw(self, path: str, json_body: dict = None) -> dict:
        """Make an authenticated POST request to a Reactor API path with a JSON body.

        Used by the debug page to proxy /search calls, which require POST by the
        Reactor API's design despite being a read-only search operation.

        Args:
            path:      API path, e.g. '/search'
            json_body: Request body as a dict (sent as application/vnd.api+json)

        Returns:
            Parsed JSON response body
        """
        post_headers = dict(self._headers())
        post_headers['Content-Type'] = 'application/vnd.api+json'
        url = f"{REACTOR_BASE_URL}{path}"
        resp = requests.post(url, headers=post_headers, json=json_body or {})
        resp.raise_for_status()
        return resp.json()

    def get_raw(self, path: str, params: dict = None) -> dict:
        """Make an authenticated GET request to an arbitrary Reactor API path.

        Used by the Reactor debug page to proxy calls through Codex's credentials.

        Args:
            path:   API path, e.g. '/companies' or '/properties/PRabc/rules'
            params: Optional query parameters dict

        Returns:
            Parsed JSON response body
        """
        url = f"{REACTOR_BASE_URL}{path}"
        resp = requests.get(url, headers=self._headers(), params=params or {})
        resp.raise_for_status()
        return resp.json()

    def get_rule_components(self, rule_id: str) -> list:
        """Fetch all components for a single rule."""
        url = f"{REACTOR_BASE_URL}/rules/{rule_id}/rule_components"
        return self._get_all_pages(url, params={"page[size]": 100})

    def get_rule(self, rule_id: str) -> dict:
        """Fetch a single rule by ID.

        Returns the rule's 'data' object, or an empty dict on failure.
        """
        resp = self.get_raw(f"/rules/{rule_id}")
        return resp.get("data", {})

    def search_dimension(self, dimension_value: str, property_id: str, size: int = 100) -> list:
        """Search all property resources for any reference to a dimension string.

        Uses the Reactor /search API to find rules, rule components, data elements,
        and extensions whose attributes contain the given dimension value. Unlike
        the library-walk approach, this is not scoped to the production library
        and finds matches in custom code actions as well as structured setVariables.

        Args:
            dimension_value: Dimension string to search for, e.g. 'eVar1', 'prop5', 'event3'.
            property_id:     Reactor property ID (PR...).
            size:            Maximum number of results to return (default 100).

        Returns:
            Raw list of matched resource dicts from the Reactor API.
        """
        body = {
            "data": {
                "from": 0,
                "size": size,
                "query": {
                    "attributes.*":                   {"value": dimension_value},
                    "relationships.property.data.id": {"value": property_id},
                    "attributes.deleted_at":          {"exists": False},
                    "attributes.revision_number":     {"value": 0},
                },
                "sort": [{"attributes.updated_at": "desc"}],
                "resource_types": ["rules", "rule_components", "data_elements", "extensions"],
            }
        }
        resp = self.post_raw("/search", body)
        return resp.get("data", [])

    def search_and_resolve(self, dimension_value: str, property_id: str) -> list:
        """Search for a dimension and resolve rule names for rule_component matches.

        Calls search_dimension() then batch-fetches the parent rules for any
        rule_component results so we can display the rule name. Deduplicates
        so the same rule only appears once even if multiple of its components match.
        rule_component entries take precedence over rule-name matches for the
        same rule_id (component matches are more informative).

        Each returned dict is compatible with the related_launch_rules_section macro:
            source:                 'rule' | 'extension' | 'data_element'
            source_id:              extension/data-element ID (for Launchpad deep link)
            rule_id:                rule ID (for Launchpad deep link)
            rule_name:              display name
            rule_enabled:           bool
            delegate_descriptor_id: action type hint, e.g. 'adobe-analytics::actions::setVariables'

        Args:
            dimension_value: e.g. 'eVar1', 'prop5', 'event3'
            property_id:     Reactor property ID (PR...)

        Returns:
            Deduplicated list of display-ready dicts.
        """
        raw_results = self.search_dimension(dimension_value, property_id)

        # Collect unique rule IDs needed from rule_component matches
        rule_ids = {
            item["relationships"]["rule"]["data"]["id"]
            for item in raw_results
            if item.get("type") == "rule_components"
            and item.get("relationships", {}).get("rule", {}).get("data", {}).get("id")
        }

        # Batch-fetch rule metadata in parallel
        rule_map: dict = {}
        if rule_ids:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(self.get_rule, rid): rid for rid in rule_ids}
                for future in as_completed(futures):
                    rid = futures[future]
                    try:
                        rule_map[rid] = future.result()
                    except Exception:
                        logger.warning("Failed to fetch rule %s for search results", rid)
                        rule_map[rid] = {}

        entries = []
        seen: set = set()

        # Process rule_components first so they take precedence over rule-name matches
        # for the same rule_id (component matches carry a delegate_descriptor_id).
        for item in raw_results:
            if item.get("type") != "rule_components":
                continue
            attrs = item.get("attributes", {})
            rule_id = (item.get("relationships", {})
                           .get("rule", {}).get("data", {}).get("id"))
            key = ("rule", rule_id)
            if key in seen:
                continue
            seen.add(key)
            rule_data = rule_map.get(rule_id, {})
            rule_attrs = rule_data.get("attributes", {})
            entries.append({
                "source":                  "rule",
                "source_id":               None,
                "rule_id":                 rule_id,
                "rule_name":               rule_attrs.get("name", "Unknown Rule"),
                "rule_enabled":            rule_attrs.get("enabled", True),
                "delegate_descriptor_id":  attrs.get("delegate_descriptor_id", ""),
            })

        # Then process extensions, data_elements, and rules (rule-name matches)
        for item in raw_results:
            item_type = item.get("type")
            attrs = item.get("attributes", {})

            if item_type == "extensions":
                key = ("extension", item["id"])
                if key in seen:
                    continue
                seen.add(key)
                entries.append({
                    "source":                  "extension",
                    "source_id":               item["id"],
                    "rule_id":                 None,
                    "rule_name":               attrs.get("display_name") or attrs.get("name") or "Extension",
                    "rule_enabled":            attrs.get("enabled", True),
                    "delegate_descriptor_id":  attrs.get("delegate_descriptor_id", ""),
                })

            elif item_type == "data_elements":
                key = ("data_element", item["id"])
                if key in seen:
                    continue
                seen.add(key)
                entries.append({
                    "source":                  "data_element",
                    "source_id":               item["id"],
                    "rule_id":                 None,
                    "rule_name":               attrs.get("name", "Data Element"),
                    "rule_enabled":            attrs.get("enabled", True),
                    "delegate_descriptor_id":  attrs.get("delegate_descriptor_id", ""),
                })

            elif item_type == "rules":
                key = ("rule", item["id"])
                if key in seen:
                    continue
                seen.add(key)
                entries.append({
                    "source":                  "rule",
                    "source_id":               None,
                    "rule_id":                 item["id"],
                    "rule_name":               attrs.get("name", "Unknown Rule"),
                    "rule_enabled":            attrs.get("enabled", True),
                    "delegate_descriptor_id":  "",
                })

        logger.info(
            "search_and_resolve('%s', '%s') → %d results (%d raw)",
            dimension_value, property_id, len(entries), len(raw_results),
        )
        return entries
