# TODOs and Bugs

This document is a list of smaller todo items and bugs found while using the Codex app.

## TODOs

- [ ] Add the allocation and expiration data to the data dimensions listing page. The data is visible on the details page, but not the listing pages
- [x] Change the data dimensions listing page template name. Renamed `table.html` → `listing.html` (autopsy 019)
- [ ] Create a debug page where I can interact with all of the API 1.4 and API 2.0 endpoints described in:
  - [adobe_analytics_api_1.4_swagger.json](adobe_analytics_api_1.4_swagger.json)
  - [adobe_analytics_api_2.0_swagger.json](adobe_analytics_api_2.0_swagger.json)

## Bugs

- [x] Merchandising eVar expiration data shown on the details page is not correct. A MerchVar with purchase event set as expiration, will actually display 1 Days for the expiration value. Checked with eVar39 in Coles Global Prod report suite. **Fixed in PR #26 (autopsies 016 & 017)**
- [ ] Adobe is deprecating the 1.4 version of the Analtytics api. It's not supposed to happen until August 2026, but already we am seeing times (usually for a few hours at a time) where the api.omniture.com endpoints become unresponsive, or the dns won't resolve, or the servers don't answer. Need to find a way to:
  1. Try alternative API domains. Alternative API endpoint domains will be on o: api2.omniture.com, api3.omniture.com, api4.omniture.com
  2. Display a fallback error message. Still show the global navigation, footer, body styling, but replace with a user friendly error message advising the API is not responding, and the data is not available, and to try again later.