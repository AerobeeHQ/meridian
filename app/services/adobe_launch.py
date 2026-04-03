"""
Adobe Experience Platform Tags (Reactor) API client.

Uses the Reactor /search API to find all property resources (rules, rule
components, data elements, extensions) that reference a given Analytics
dimension string (e.g. 'eVar1', 'prop5', 'event3').

This approach is not scoped to the production library and matches custom
code actions as well as structured setVariables actions, giving a more
complete picture than walking the library graph.
"""
import json
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
        self._reactor_company_id: str | None = None

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

    def get_company_id(self) -> str | None:
        """
        Return the Reactor company ID (``CO...``) for the authenticated org.

        Fetches ``GET /companies`` once and caches the result on the instance.
        Returns ``None`` if the call fails or the response is empty so callers
        can degrade gracefully.
        """
        if self._reactor_company_id is not None:
            return self._reactor_company_id

        try:
            resp = self.get_raw("/companies")
            companies = resp.get("data", [])
            if companies:
                self._reactor_company_id = companies[0].get("id")
                logger.info("Reactor company ID: %s", self._reactor_company_id)
        except Exception:
            logger.warning("Failed to fetch Reactor company ID from /companies")

        return self._reactor_company_id

    def get_tags_base_url(self, org_alias: str | None) -> str | None:
        """
        Build the base URL for the Adobe Experience Platform Tags (Launch) UI.

        The returned string ends before the property path, e.g.::

            https://experience.adobe.com/#/@originenergy/sname:prod/data-collection/tags/companies/COabc123

        Callers append ``/properties/{property_id}/rules/{rule_id}`` etc.

        Args:
            org_alias: The ``EXPERIENCE_CLOUD_ORG`` config value (e.g. ``"originenergy"``).
                       Returns ``None`` when absent.

        Returns:
            URL string, or ``None`` when either identifier is unavailable.
        """
        if not org_alias:
            return None
        company_id = self.get_company_id()
        if not company_id:
            return None
        return (
            f"https://experience.adobe.com/#/@{org_alias}"
            f"/sname:prod/data-collection/tags/companies/{company_id}"
        )

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

    def _get_first_rule_for_component(self, rules_url: str) -> dict:
        """Fetch the first rule for a component via its links.rules URL.

        The Reactor API does not always populate relationships.rule.data.id in
        search results. This fallback GETs the component's rules relationship
        URL (e.g. /rule_components/{id}/rules) and returns the first rule object,
        or an empty dict if none are found.
        """
        resp = requests.get(rules_url, headers=self._headers())
        resp.raise_for_status()
        rules = resp.json().get("data", [])
        return rules[0] if rules else {}

    @staticmethod
    def _parse_set_variables_settings(settings_raw: str) -> list[dict]:
        """Parse an ``adobe-analytics::actions::setVariables`` settings JSON string.

        Extracts the variable assignments (eVars, props, events) into a flat list
        of dicts, each with ``variable`` and ``value`` keys.  ``value`` may be a
        constant string or a ``%dataElement%`` reference.

        Returns an empty list if the settings cannot be parsed or is empty.
        """
        if not settings_raw:
            return []
        try:
            settings = json.loads(settings_raw)
        except (ValueError, TypeError):
            return []

        assignments: list[dict] = []
        tracker = settings.get("trackerProperties", {})

        for evar in tracker.get("evars", {}).get("evars", []):
            name = evar.get("name", "")
            if name:
                assignments.append({"variable": name, "value": evar.get("value", "")})

        for prop in tracker.get("props", {}).get("props", []):
            name = prop.get("name", "")
            if name:
                assignments.append({"variable": name, "value": prop.get("value", "")})

        for event in tracker.get("events", {}).get("events", []):
            name = event.get("name", "")
            if name:
                assignments.append({"variable": name, "value": event.get("value", "")})

        return assignments

    def search_and_resolve(self, dimension_value: str, property_id: str) -> list:
        """Search for a dimension and resolve rule names for rule_component matches.

        Calls search_dimension() then resolves the parent rule name for each
        rule_component result using one of two strategies, run in parallel:

        - Strategy A (relationships.rule.data.id present):
            GET /rules/{id} — standard single-rule fetch.
        - Strategy B (relationship ID absent, links.rules present):
            GET {links.rules} — returns the list of parent rules for the component.
            Used when the /search response omits the relationship data.

        Deduplicates so the same rule only appears once. rule_component entries
        take precedence over rule-name matches for the same rule_id.

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

        # Categorise rule_component items by resolution strategy.
        # strategy_a: rule_id  -> [component_item, ...]  (fetch rule via GET /rules/{id})
        # strategy_b: comp_id  -> url                    (fetch rule via GET {links.rules})
        # component_by_rule groups all component items per rule_id so we can
        # later aggregate variable_assignments across multiple setVariables actions.
        strategy_a: dict[str, list] = {}
        strategy_b: dict[str, str] = {}
        component_by_rule: dict[str, list] = {}   # rule_id -> [comp_item, ...]
        component_by_comp: dict[str, list] = {}   # comp_id -> [comp_item] (for strategy B)

        for item in raw_results:
            if item.get("type") != "rule_components":
                continue
            rel_id = (item.get("relationships", {})
                          .get("rule", {}).get("data", {}).get("id"))
            if rel_id:
                strategy_a.setdefault(rel_id, []).append(item)
                component_by_rule.setdefault(rel_id, []).append(item)
            else:
                rules_url = item.get("links", {}).get("rules")
                if rules_url:
                    strategy_b[item["id"]] = rules_url
                    component_by_comp.setdefault(item["id"], []).append(item)

        # Single executor pass for both strategies.
        # rule_map:  rule_id  -> rule data object  (strategy A results)
        # comp_map:  comp_id  -> rule data object  (strategy B results)
        rule_map: dict = {}
        comp_map: dict = {}

        tasks: dict = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            for rule_id in strategy_a:   # strategy_a is now rule_id -> [items]
                fut = executor.submit(self.get_rule, rule_id)
                tasks[fut] = ("a", rule_id)
            for comp_id, url in strategy_b.items():
                fut = executor.submit(self._get_first_rule_for_component, url)
                tasks[fut] = ("b", comp_id)

            for future in as_completed(tasks):
                strategy, id_ = tasks[future]
                try:
                    result = future.result()
                    if strategy == "a":
                        rule_map[id_] = result
                    else:
                        comp_map[id_] = result
                except Exception:
                    logger.warning(
                        "Failed to resolve rule (strategy %s, id %s)", strategy, id_
                    )
                    if strategy == "a":
                        rule_map[id_] = {}
                    else:
                        comp_map[id_] = {}

        entries = []
        seen: set = set()

        # Process rule_components first so they take precedence over rule-name matches
        # for the same rule_id (component matches carry a delegate_descriptor_id).
        for item in raw_results:
            if item.get("type") != "rule_components":
                continue
            attrs = item.get("attributes", {})

            # Resolve rule data — try strategy A first, fall back to B
            rule_id = (item.get("relationships", {})
                           .get("rule", {}).get("data", {}).get("id"))
            if rule_id:
                rule_data = rule_map.get(rule_id, {})
            else:
                rule_data = comp_map.get(item["id"], {})
                rule_id = rule_data.get("id")   # extract for Launchpad deep link

            rule_attrs = rule_data.get("attributes", {})
            key = ("rule", rule_id)
            if key in seen:
                continue
            seen.add(key)

            # Aggregate variable assignments from all setVariables components for
            # this rule (a rule may have more than one setVariables action).
            variable_assignments: list[dict] = []
            all_components = (component_by_rule.get(rule_id, [])
                              or component_by_comp.get(item["id"], []))
            for comp in all_components:
                comp_attrs = comp.get("attributes", {})
                if comp_attrs.get("delegate_descriptor_id", "").endswith("::actions::setVariables"):
                    variable_assignments.extend(
                        self._parse_set_variables_settings(comp_attrs.get("settings", ""))
                    )

            entries.append({
                "source":                  "rule",
                "source_id":               None,
                "rule_id":                 rule_id,
                "rule_name":               rule_attrs.get("name", "Unknown Rule"),
                "rule_enabled":            rule_attrs.get("enabled", True),
                "delegate_descriptor_id":  attrs.get("delegate_descriptor_id", ""),
                "variable_assignments":    variable_assignments,
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
