# Fix: Adobe API Event Logging

**Date:** December 11, 2025  
**Issue:** Needed insight into `ReportSuite.GetEvents` responses while debugging missing data

## Summary
Added structured logging to the Adobe Analytics service so each HTTP request logs payload metadata, response status/encoding, and fallback decoding outcomes—making it easier to inspect event responses from PyCharm's Run console.

## Actions Taken
1. Imported `logging` in `app/services/adobe_analytics.py` and created a module-level logger.
2. Instrumented `_make_request`, `_fetch_with_manual_decoding`, `_decode_raw_response`, and `get_success_events` with helpful `debug`/`warning` messages covering payload keys, response headers, manual retries, and final event counts.
3. Verified the service still runs via a short script (`logging.basicConfig(level=logging.DEBUG)` + `get_success_events`), ensuring the new logs appear without errors.

## Verification
1. `python - <<'PY' ... get_success_events ... PY` (emits new debug logs)

## Next Steps
1. Re-run the Flask app and inspect the PyCharm Run console while loading `/events` to capture the logged request/response details.
2. Use the detailed logs to continue diagnosing why the Adobe API returns no event rows for `mdptnrdev`.

