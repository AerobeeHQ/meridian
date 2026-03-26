# TODOs and Bugs

This document is a list of smaller todo items and bugs found while using the Codex app.

## TODOs

- [x] Add the allocation and expiration data to the data dimensions listing page. The data is visible on the details page, but not the listing pages
- [x] Change the data dimensions listing page template name. Renamed `table.html` → `listing.html` ([autopsy 019](.docs/autopsies/019-rename-table-template.md))
- [x] Add a Segments listing page (API 2.0 `/segments` endpoint). See [autopsy 025](.docs/autopsies/025-segments-listing.md).
- [x] Add a Calculated Metrics listing and detail page (API 2.0 `/calculatedmetrics` endpoint). See [autopsy 027](.docs/autopsies/027-calculated-metrics.md).
- [ ] Create a debug page where I can interact with all of the API 1.4 and API 2.0 endpoints described in:
  - [adobe_analytics_api_1.4_swagger.json](adobe_analytics_api_1.4_swagger.json)
  - [adobe_analytics_api_2.0_swagger.json](adobe_analytics_api_2.0_swagger.json)
- [x] Update the "Report Suites" page and shows all the report suites in the authenticated Adobe Analytics company, and key summary data about each one (e.g., which report suite has the most eVars, or which report suite has the most recent change date). **Fixed in [feature/report-suites-page](.docs/autopsies/031-report-suites-page.md)**
- [x] Cleanup the display of monospace text on the Processing Rules pages. It's a bit smaller than other text, and other pages like Segment Details use a pink monospace font that looks a bit more at home in the app. So maybe use that style instead? **Fixed in [fix/processing-rules-monospace](.docs/autopsies/030-processing-rules-monospace.md)**
- [x] Consolidate the Marketing Channels and Channel Rules into one dropdown to save space on the global navigation. See [autopsy 026](.docs/autopsies/026-channels-nav-dropdown.md).
- [ ] Consolidate this todo.md file into the version-2-roadmap.md file.
- [ ] Add a "Known Issues" section to the README that links to this list of bugs, so users are aware of any current limitations or issues with the app.
- [x] Update the README and make sure it is up to date with the latest changes.
- [ ] Add a "Version History" section to the README that lists the major changes and updates for each version of the app.
- [x] Add a panel to the props/evars/events/listvar details pages (similar to the Related Processing Rules) named "Components", and lists Segments and Calculated Metrics that use that data dimension. The user should be able to click on the component name to view the details page for that component. See [autopsy 028](.docs/autopsies/028-components-panel.md).

## Bugs

- [x] Merchandising eVar expiration data shown on the details page is not correct. A MerchVar with purchase event set as expiration, will actually display 1 Days for the expiration value. Checked with eVar39 in Coles Global Prod report suite. **Fixed in PR #26 ([autopsies 016 & 017](.docs/autopsies/016-evar-allocation-expiration-fix.md), [.docs/autopsies/017-merchandising-evar-expiration-bug.md))**
- [x] Adobe is deprecating the 1.4 version of the Analtytics api. It's not supposed to happen until August 2026, but already we am seeing times (usually for a few hours at a time) where the api.omniture.com endpoints become unresponsive, or the dns won't resolve, or the servers don't answer. Need to find a way to:
  1. Try alternative API domains. Alternative API endpoint domains will be on o: api2.omniture.com, api3.omniture.com, api4.omniture.com
  2. Display a fallback error message. Still show the global navigation, footer, body styling, but replace with a user friendly error message advising the API is not responding, and the data is not available, and to try again later.
- [x] The prop and eVar detail pages don't display any calculated metrics; but it does work for events. I think it is because a calc metric will never have the prop or evar at the top level of logic. Those data dimensions will always be nested inside a segment inside of a calculated metric. **Fixed in [fix/components-calc-metrics-transitive](.docs/autopsies/029-components-calc-metrics-transitive.md)**