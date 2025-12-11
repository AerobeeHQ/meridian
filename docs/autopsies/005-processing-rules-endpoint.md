# Investigation: Processing Rules Endpoint

**Date:** December 11, 2025  
**Issue:** Processing Rules page fails because the service calls `ReportSuite.GetProcessingRules`, but Adobe Analytics API 1.4 exposes `ReportSuite.ViewProcessingRules` for readable rule data.

## Summary
Reviewed the Flask route stack and the Adobe service implementation. Confirmed the UI fetches processing data through `get_processing_rules`, which currently posts to `ReportSuite.GetProcessingRules`. Swagger documentation and schema definitions show the public endpoint is `ReportSuite.ViewProcessingRules`, returning `report_suite_viewable_processing_rules_array`. This mismatch likely results in either a 404 from Adobe or an unexpected payload shape, so the template never receives usable data.

## Findings
1. `app/routes/main.py:/processing-rules` and its export path both depend on `AdobeAnalyticsService.get_processing_rules`.
2. `app/services/adobe_analytics.py:get_processing_rules` calls `ReportSuite.GetProcessingRules` and then attempts to guess response shapes (`processing_rules`, `rules`, `ruleNum`). No schema in swagger matches that response, indicating the method name is wrong.
3. Swagger (`docs/adobe_analytics_api_1.4_swagger.json`, lines 5224-5262 & 12548-13525) documents only `ReportSuite.ViewProcessingRules`, which accepts `rsid_list` and returns `processing_rules` nested under each rsid.
4. Because the service never receives the expected `processing_rules`, the cache stores either empty arrays or error payloads, so the Processing Rules page renders nothing.

## Actions Taken
1. Updated `app/services/adobe_analytics.py:get_processing_rules` to call `ReportSuite.ViewProcessingRules` and parse the documented `processing_rules` array.
2. Normalized the rules into simple rows (rule number, title, match, conditions, actions, comment) so `table.html` can render them.
3. Ran `python verify_setup.py` and `python run.py` (no console output in this environment) to ensure the app still boots.

## Next Steps
1. Clear cached processing rules (`cache/`) so the UI fetches fresh data.
2. Reload `/processing-rules` in the Flask app to confirm rule rows now render.
3. Monitor logs for any "Unexpected processing rules response" warnings in case Adobe changes the payload again.
4. Consider surfacing ELSE actions in a dedicated column if analysts need separate visibility.
