# Handoff: Codex → Meridian Rebrand

## Context

This repo (currently "Codex") is being renamed to **Meridian** to avoid confusion with OpenAI's Codex product. Codex is a Python/Flask app that visualises Adobe Analytics configurations (eVars, props, events, processing rules) — see `AGENTS.md` in the repo root first for full architectural and coding-convention context before touching anything.

Repo: `gitlab.maxisdev.com/mc/codex` (project ID 82). The GitLab project itself keeps the name `codex` until Phase 6 — GitLab preserves redirects after a project rename, so renaming it is a safe, low-risk step done last.

## Naming decisions (final)

- Display name: **Meridian**
- Lowercase / slug / config-key form: `meridian`
- Tagline: unchanged from Codex — no copy rewrite needed, just swap the product name
- New domain: `meridian.aerobee.com.au` (consistent with the Mission Control product line's recent migration to Aerobee)
- Old domain `codex.maxisdev.com`: handled via a 301 redirect using **Cloudflare Page Rules** — not a Flask route, so no app code needed for this

## Work tracking

All work is tracked as GitLab issues on project 82 (`mc/codex`), labelled `rebrand`, and cross-linked in sequence:

| Issue | Phase | Owner |
|---|---|---|
| [#93](https://gitlab.maxisdev.com/mc/codex/-/work_items/93) | Decisions & prep | Done (1 minor item open) |
| [#94](https://gitlab.maxisdev.com/mc/codex/-/work_items/94) | **Codebase updates** | **Claude Code — this is your scope** |
| [#95](https://gitlab.maxisdev.com/mc/codex/-/work_items/95) | Infrastructure (Cloudflare + LXC) | Joris (manual/GUI) |
| [#96](https://gitlab.maxisdev.com/mc/codex/-/work_items/96) | Promo site rebrand | Joris (content + Affinity assets) |
| [#97](https://gitlab.maxisdev.com/mc/codex/-/work_items/97) | Testing & cutover | Shared |
| [#98](https://gitlab.maxisdev.com/mc/codex/-/work_items/98) | Cleanup (repo rename, retire old domain) | Joris (manual, last step) |

## Your scope: Issue #94 — Codebase updates

- [ ] `pyproject.toml`: update `name` field
- [ ] `config.json` / `config.dist.json`: update `APP_TITLE` to Meridian
- [ ] Global search for `Codex`/`codex` across the repo (templates, routes, comments, log messages, cache key prefixes, export filenames); replace where user-facing or semantically meaningful — leave incidental/unrelated matches alone
- [ ] `AGENTS.md`: update project name/description throughout
- [ ] `README.md`: update project name/description
- [ ] `app/services/cache.py`: check cache filenames/directory names for "codex" references, rename if present (safe to invalidate — cache has hourly expiry)
- [ ] `notebooks/`: check for hardcoded titles/labels
- [ ] `verify_setup.py`: update any printed app name in health-check output
- [ ] `app/templates/`: check `<title>` tags, headers, favicon references

## House rules (from AGENTS.md — follow these)

- **MVP velocity philosophy**: no unit tests, manual testing only. Verify with `uv run verify_setup.py` and `uv run run.py` (port 5010).
- **Python beginner-friendly**: Joris has a strong JS background but is a Python beginner. Prefer clear, readable code over "clever"/idiomatic Python.
- **No Node/npm tooling** in this repo under any circumstances — hard constraint.
- Never log credentials. `config.json` is git-ignored; only edit `config.dist.json` as the template if adding new required keys.
- Wrap new API calls through `cache.get_or_set(...)` per existing convention; don't bypass caching.

## Explicitly out of scope for this agent

- Cloudflare Zero Trust tunnel configuration, DNS, Page Rules (#95) — GUI-only, Joris manages this directly
- Affinity logo/favicon/image asset creation (#96)
- GitLab project rename (#98) — manual, done last, do not attempt

## Suggested workflow

1. Read `AGENTS.md`, then this document.
2. Work through the #94 checklist above.
3. Run `uv run verify_setup.py` and a manual smoke test (`uv run run.py`, check the UI shows "Meridian" everywhere, no leftover "Codex" strings).
4. Commit with a message referencing `#94` (e.g. `Closes #94` if opening an MR, or a normal reference if committing directly) so GitLab links the work automatically.
5. Stop after #94 — do not proceed into #95–#98, those are manual/GUI-driven phases owned by Joris.
