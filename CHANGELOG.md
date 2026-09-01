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

### Added

- Playbook upgrades ([#1](https://github.com/k7cfo/remove-your-data/issues/1)): `STATUS.md` (verified / untested / defunct), `references/dead-urls.md` (loaded by `ryd.py pack`), named **file** vs **verify** pass, `relist_90d` clock, roster allowlist (`keep_host` / `keep_url`), `docs/PRIVACY.md`, `scripts/registry_pull.py` (hostname diff, no spray), `templates/regulator-complaint.md`, SERP new-host watch (`exports/serp-hosts.txt`). Queue gaps confirmed live where the form answered 200 (SmartBackgroundChecks, InfoTracer, SocialCatfish); PeekYou / PeopleSmart / SearchPeopleFree / PeopleSearchNow listed `untested` (datacenter 403); PublicDataUSA and Open Data USA origin marked `defunct`. Clearbit opt-out 404 → HubSpot privacy preferences.
- Intake asks onboarding questions **one at a time** ([#5](https://github.com/k7cfo/remove-your-data/issues/5)); do not dump the questionnaire.

### Changed

- Field notes: ContactOut Turnstile + `support@` fallback; TruePeopleSearch `.net` Google Form needs a signed-in consumer Google; Spokeo empty `/optout` → `privacy@`; Open Data USA null-MX / leftover vehicle cards / letter after the contact window / parked origin cancels the letter (confirm via browser + RDAP); origin timeout is not a drop; PeopleConnect name-index teasers can go quiet then resurface; curl CF vs browser can disagree; hourly CF after a live reading is opacity; Radaris city-only skip; ~90-day re-list clock; Whitepages Zendesk auto-ack may omit California (reply on the same thread); CheckPeople written expunge vs ~48h CF lag, then Google name-index can still snippet PII while origin is CF (do not refile); MyLife 410 can still SERP; National Public Data `/optout.html` Turnstile + `support@` fallback.

