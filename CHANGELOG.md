# Changelog

All notable changes to this project. Dates are UTC.

## 0.1.0 — 2026-08-29

First public drop. Agent-first skill + localhost app.

### Added

- `SKILL.md` playbook: intake, CA DROP first, free broker opt-outs, SQLite legal log, no paid deletion services
- Localhost dashboard (`scripts/ryd.py serve`) and stdlib CLI (`init`, `export`, `export-csv`)
- Household **roster** (`/roster`): aliases, addresses, phones, emails, family members; per-person consent; unique verify emails
- CLI: `add-person`, `add-ident`, `pack`
- **Settings** gear (`/settings`): cadence, pause, anonymity, timezone, dashboard refresh; CLI `settings --show` / `--cadence` / `--paused`
- Google **Results about you** / SERP ⋮ Remove result as last failsafe after broker opt-outs; Bing content removal next
- Search catalog in `references/search.md` (host-native, keyless engines, optional APIs)
- Agent boot: `AGENTS.md`, root `SKILL.md`, `CLAUDE.md`, `skills/remove-your-data/SKILL.md` stub

### Changed

- README is agent-first: paste the repo URL, read `AGENTS.md` then `SKILL.md`. Do not fork; open PRs here. License at the bottom.

## Unreleased

### Changed

- Field notes: ContactOut Turnstile + `support@` fallback; TruePeopleSearch `.net` Google Form needs a signed-in consumer Google; Spokeo empty `/optout` → `privacy@`; Open Data USA null-MX / leftover vehicle cards / letter after the contact window; origin timeout is not a drop; PeopleConnect name-index teasers; Radaris city-only skip; ~90-day re-list clock.

