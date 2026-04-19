Version 3 Roadmap

This document summarises the planned features for Codex v3. Each item has a detailed implementation plan in `docs/plans/`.

## Ideas
- Settings to choose a specific report suite
- Settings to map the Adobe Launch property to the chosen report suite
- Offer [Adobe Spectrum](https://github.com/adobe/spectrum-web-components/blob/main/CONTRIBUTOR-DOCS/README.md) as a theme option.
- User OAuth login — Largest architectural change. Config scaffolding is in place (AUTH_MODE, OAUTH_REDIRECT_URI, SESSION_SECRET); full per-user flow not yet implemented.
- Develop a plan for dealing with the shutdown of Adobe Analytics API v1.4, which is currently used for some features. API v2 doesn't have the same features, so look into having the user extract the information from Adobe themselves, or having an AI agent, or playwright script login on the user's behalf and extract the information from the Adobe Analytics UI.
- Remove dependency on third parties for CSS, icons, theme, or look into hosting these assets ourselves.
- Continue with documenting how to setup and run Codex.
- Write unit tests for all components and functions