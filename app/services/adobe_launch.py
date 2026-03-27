"""
Adobe Experience Platform Tags (Reactor) API client.

Fetches two sources of Analytics variable assignments from the production library:

1. **Extension configuration** — variables set globally in the Adobe Analytics
   extension (trackerProperties.eVars / props / events). These are applied on
   every hit, regardless of which rules fire.

2. **Rule Set Variables actions** — per-rule analytics actions that conditionally
   set variables when a rule fires (delegate_descriptor_id contains "setVariables").

Reactor API quirk: the `settings` field on extensions and rule components is a
JSON *string*, not a parsed object — always json.loads() before use.
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from app.services.adobe_auth import OAuth2Auth

logger = logging.getLogger(__name__)

REACTOR_BASE_URL = "https://reactor.adobe.io"
_ANALYTICS_EXTENSION_NAME = "adobe-analytics"
_SET_VARIABLES_ACTION = "setVariables"


def _parse_settings(raw) -> dict:
    """Parse a settings value that may be a JSON string or an already-parsed dict."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return raw or {}


def _extract_names(items: list) -> list:
    """Extract non-empty 'name' fields from a list of variable dicts."""
    return [item["name"] for item in items if isinstance(item, dict) and item.get("name")]


def _parse_tracker_properties(settings: dict) -> tuple:
    """
    Extract eVar, prop, event, and list variable names from an Analytics
    settings dict.

    Handles two known formats:
    - Modern: {"trackerProperties": {"eVars": [...], "props": [...], "events": [...]}}
    - Legacy:  {"eVars": [...], "props": [...], "events": [...]}

    Adobe Analytics variable name casing:
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

    Fetches Analytics variable assignments from the production library and
    returns a compact, cacheable list for cross-referencing in Codex.
    Each entry has a 'source' field of either 'extension' or 'rule'.
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

    def get_library_extensions(self, library_id: str) -> list:
        """Return the full extension objects included in a library."""
        url = f"{REACTOR_BASE_URL}/libraries/{library_id}/extensions"
        return self._get_all_pages(url, params={"page[size]": 100})

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
        Return all Analytics variable assignments from the production library.

        Includes two source types, returned in a single flat list:

        Extension entry (source='extension'):
        {
            "source":       "extension",
            "source_id":    str,   # Extension ID for Launchpad deep linking
            "rule_id":      None,
            "rule_name":    "Adobe Analytics Extension",
            "rule_enabled": bool,
            "evars":        list,
            "props":        list,
            "events":       list,
            "lists":        list,
        }

        Rule entry (source='rule'):
        {
            "source":       "rule",
            "source_id":    None,
            "rule_id":      str,   # Rule ID for Launchpad deep linking
            "rule_name":    str,
            "rule_enabled": bool,
            "evars":        list,
            "props":        list,
            "events":       list,
            "lists":        list,
        }
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

        # Fetch extensions and rules in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            ext_future  = executor.submit(self.get_library_extensions, library_id)
            rule_future = executor.submit(self.get_library_rules, library_id)
            extensions  = ext_future.result()
            rules       = rule_future.result()

        actions = []

        # ── Extension-level global variables ─────────────────────────────────
        for ext in extensions:
            attrs = ext.get("attributes", {})
            if attrs.get("name") != _ANALYTICS_EXTENSION_NAME:
                continue

            settings = _parse_settings(attrs.get("settings", "{}"))
            evars, props, events, lists = _parse_tracker_properties(settings)

            if not any([evars, props, events, lists]):
                continue

            actions.append({
                "source":       "extension",
                "source_id":    ext["id"],
                "rule_id":      None,
                "rule_name":    "Adobe Analytics Extension",
                "rule_enabled": attrs.get("enabled", True),
                "evars":        evars,
                "props":        props,
                "events":       events,
                "lists":        lists,
            })

        # ── Rule Set Variables actions ────────────────────────────────────────
        if not rules:
            logger.info(
                "Fetched %d entry from extension config, 0 rules in library '%s'",
                len(actions), library_name,
            )
            return actions

        rule_meta = {
            r["id"]: {
                "name":    r.get("attributes", {}).get("name", "Unknown"),
                "enabled": r.get("attributes", {}).get("enabled", True),
            }
            for r in rules
        }

        # Fetch rule components in parallel
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

        rule_count = 0
        for rule_id, components in components_by_rule.items():
            for comp in components:
                attrs = comp.get("attributes", {})
                ddid = attrs.get("delegate_descriptor_id", "")

                if _ANALYTICS_EXTENSION_NAME not in ddid:
                    continue
                if _SET_VARIABLES_ACTION not in ddid:
                    continue

                settings = _parse_settings(attrs.get("settings", "{}"))
                evars, props, events, lists = _parse_tracker_properties(settings)

                if not any([evars, props, events, lists]):
                    continue

                meta = rule_meta.get(rule_id, {})
                actions.append({
                    "source":       "rule",
                    "source_id":    None,
                    "rule_id":      rule_id,
                    "rule_name":    meta.get("name", "Unknown"),
                    "rule_enabled": meta.get("enabled", True),
                    "evars":        evars,
                    "props":        props,
                    "events":       events,
                    "lists":        lists,
                })
                rule_count += 1

        logger.info(
            "Fetched %d entries (%d extension + %d rule actions) from library '%s' for property %s",
            len(actions),
            len(actions) - rule_count,
            rule_count,
            library_name,
            property_id,
        )
        return actions
