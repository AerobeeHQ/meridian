"""
Adobe Experience Platform Tags (Reactor) API client.

Fetches rules and their Analytics Set Variables actions for cross-referencing
with Codex dimension detail pages. Only Analytics Set Variables actions are
fetched; custom-code actions are excluded.

Reactor API quirk: the `settings` field on rule components is a JSON *string*,
not a parsed object — always json.loads() before use.
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from app.services.adobe_auth import OAuth2Auth

logger = logging.getLogger(__name__)

REACTOR_BASE_URL = "https://reactor.adobe.io"
_ANALYTICS_EXTENSION_PREFIX = "adobe-analytics"
_SET_VARIABLES_ACTION = "setVariables"


def _extract_names(items: list) -> list:
    """Extract non-empty 'name' fields from a list of variable dicts."""
    return [item["name"] for item in items if isinstance(item, dict) and item.get("name")]


def _parse_variable_names(settings: dict) -> tuple:
    """
    Extract eVar, prop, event, and list variable names from setVariables settings.

    Handles two known formats:
    - Modern: {"trackerProperties": {"eVars": [...], "props": [...], "events": [...]}}
    - Legacy:  {"eVars": [...], "props": [...], "events": [...]}

    Variable name casing follows Adobe conventions:
    - eVars: "eVar1", "eVar2", … (capital V)
    - props:  "prop1", "prop2", …
    - events: "event1", "event2", …
    - lists:  "list1", "list2", "list3"
    """
    tracker = settings.get("trackerProperties", settings)
    evars  = _extract_names(tracker.get("eVars")   or tracker.get("evars")    or [])
    props  = _extract_names(tracker.get("props")   or [])
    events = _extract_names(tracker.get("events")  or [])
    lists  = _extract_names(tracker.get("lists")   or tracker.get("listVars") or [])
    return evars, props, events, lists


class AdobeLaunchService:
    """
    Client for the Adobe Experience Platform Reactor (Tags) API.

    Fetches all Analytics Set Variables rule actions for a property and
    returns a compact, cacheable list for cross-referencing in Codex.
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
            resp.raise_for_status()
            body = resp.json()
            results.extend(body.get("data", []))
            url = body.get("links", {}).get("next")
            params = None  # Subsequent pages use the full URL from links.next
        return results

    def get_production_library(self, property_id: str) -> dict | None:
        """Return the most recently updated published library for a property.

        Returns None if no published library exists.
        """
        url = f"{REACTOR_BASE_URL}/properties/{property_id}/libraries"
        libraries = self._get_all_pages(url, params={
            "filter[state]": "EQ published",
            "page[size]": 100,
        })
        if not libraries:
            return None
        return max(libraries, key=lambda lib: lib.get("attributes", {}).get("updated_at", ""))

    def get_library_rules(self, library_id: str) -> list:
        """Return the full rule objects included in a library."""
        url = f"{REACTOR_BASE_URL}/libraries/{library_id}/rules"
        return self._get_all_pages(url, params={"page[size]": 100})

    def get_rule_components(self, rule_id: str) -> list:
        """Fetch all components for a single rule."""
        url = f"{REACTOR_BASE_URL}/rules/{rule_id}/rule_components"
        return self._get_all_pages(url, params={"page[size]": 100})

    def get_analytics_actions(self, property_id: str) -> list:
        """
        Return all Analytics Set Variables actions from the production library.

        Only rules in the most recently published library are inspected —
        Development and Staging library contents are deliberately excluded.

        Each item in the returned list is a compact dict:
        {
            "rule_id":      str,   # Reactor rule ID (RL...)
            "rule_name":    str,   # Human-readable rule name
            "rule_enabled": bool,  # Whether the rule is active
            "evars":        list,  # ["eVar1", "eVar5", ...]
            "props":        list,  # ["prop1", ...]
            "events":       list,  # ["event2", ...]
            "lists":        list,  # ["list1", ...]
        }

        Rule components are fetched in parallel (8 workers) to keep total
        fetch time reasonable for properties with many rules.
        """
        # Scope to the production library only
        library = self.get_production_library(property_id)
        if library is None:
            logger.warning(
                "No published library found for property %s — Launch cache will be empty",
                property_id,
            )
            return []

        library_id = library["id"]
        library_name = library.get("attributes", {}).get("name", "Unknown")
        logger.info("Using production library '%s' (%s)", library_name, library_id)

        rules = self.get_library_rules(library_id)
        if not rules:
            return []

        rule_meta = {
            r["id"]: {
                "name":    r.get("attributes", {}).get("name", "Unknown"),
                "enabled": r.get("attributes", {}).get("enabled", True),
            }
            for r in rules
        }

        # Fetch rule components in parallel to reduce total wait time
        components_by_rule: dict = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(self.get_rule_components, rule_id): rule_id
                for rule_id in rule_meta
            }
            for future in as_completed(futures):
                rule_id = futures[future]
                try:
                    components_by_rule[rule_id] = future.result()
                except Exception:
                    logger.warning("Failed to fetch components for rule %s", rule_id)
                    components_by_rule[rule_id] = []

        actions = []
        for rule_id, components in components_by_rule.items():
            for comp in components:
                attrs = comp.get("attributes", {})
                ddid = attrs.get("delegate_descriptor_id", "")

                # Only interested in Analytics extension Set Variables actions
                if _ANALYTICS_EXTENSION_PREFIX not in ddid:
                    continue
                if _SET_VARIABLES_ACTION not in ddid:
                    continue

                # The Reactor API returns settings as a JSON string, not a dict
                raw = attrs.get("settings", "{}")
                if isinstance(raw, str):
                    try:
                        settings = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        settings = {}
                else:
                    settings = raw or {}

                evars, props, events, lists = _parse_variable_names(settings)
                if not any([evars, props, events, lists]):
                    continue  # Skip actions that set no recognisable variables

                meta = rule_meta.get(rule_id, {})
                actions.append({
                    "rule_id":      rule_id,
                    "rule_name":    meta.get("name", "Unknown"),
                    "rule_enabled": meta.get("enabled", True),
                    "evars":        evars,
                    "props":        props,
                    "events":       events,
                    "lists":        lists,
                })

        logger.info(
            "Fetched %d Analytics Set Variables actions from %d rules in library '%s' for property %s",
            len(actions), len(rules), library_name, property_id,
        )
        return actions
