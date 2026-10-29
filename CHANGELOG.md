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

- README is agent-first: paste the repo URL, read `AGENTS.md` then `SKILL.md`. Open PRs here. License at the bottom.

## Unreleased

- **License:** relicensed to Apache-2.0 by the sole copyright holder, Nick Newsom (@k7cfo). Added `NOTICE` and `CITATION.cff`; forks are welcome, keep `NOTICE`.
- **Chat-first reporting:** new `ryd.py recap` (read-only session-start summary with a ledger digest) and `ryd.py report` (`--md` default, `--text`, `--json`, `--image` PNG status card; Pillow optional, `RYD_NO_PIL=1` forces the built-in renderer). Output has vendor names, statuses, counts, and relative due dates only. Agents run `recap` first every session and present the card in chat; the dashboard is an optional view.

- Note standalone LinkedIn scrapers / professional people directories without home phone or address are out of scope.

### Changed
- Whitepages Zendesk "could not locate any listings" / "may already be removed" + screenshot ask is not a close when Property Intel (or another sibling URL) is still origin 200 with matching owner/address identifiers — reply same-thread with exact URL + dated screenshot; agents often search people profiles only. Partial resident/landline scrub while owner/trust/street remain is not a full drop; keep the leftover and escalation clock open (stale SERP may still show scrubbed residents).
- Radaris-class court-order / records-transferred landings with no matching identifiers are not a refile. After a clean origin 404, later CF/JS 403 on subject and control URLs the same hour is site-wide opacity, not a reappear.
- Google Results-about-you / SERP Remove approval for one URL is not an origin drop (recheck live page; CF/JS 403 ≠ 404). Whitepages address pages and Property Intel are separate leftovers — hiding one does not take the other down.
- Human-needed tracker hygiene: keep SERP account removals deferred/last-step while people-search origins are still live; close or demote Turnstile/form human rows after a written vendor confirm; keep ops UI human section in sync with the tracker.

### Added

- Privacy landscape ([#7](https://github.com/k7cfo/remove-your-data/issues/7)): person-scoped `/landscape`, inline offline SVG globe, explicit operator-region metadata and Unknown counts, SQLite-triggered status history with honest legacy baselines, and a paused keyboard-operable timeline. Reduced-motion/manual controls and no-JavaScript current counts; aggregate-only JSON with no external resources. Regression coverage includes chronology, simultaneous events, isolation, Unknown, script escaping, and privacy boundaries.
- Playbook upgrades ([#1](https://github.com/k7cfo/remove-your-data/issues/1)): `STATUS.md` (verified / untested / defunct), `references/dead-urls.md` (loaded by `ryd.py pack`), named **file** vs **verify** pass, `relist_90d` clock, roster allowlist (`keep_host` / `keep_url`), `docs/PRIVACY.md`, `scripts/registry_pull.py` (hostname diff, no spray), `templates/regulator-complaint.md`, SERP new-host watch (`exports/serp-hosts.txt`). Queue gaps confirmed live where the form answered 200 (SmartBackgroundChecks, InfoTracer, SocialCatfish); PeekYou / PeopleSmart / SearchPeopleFree / PeopleSearchNow listed `untested` (datacenter 403); PublicDataUSA and Open Data USA origin marked `defunct`. Clearbit opt-out 404 → HubSpot privacy preferences.
- Intake asks onboarding questions **one at a time** ([#5](https://github.com/k7cfo/remove-your-data/issues/5)); do not dump the questionnaire.
- Harness fallbacks ([#4](https://github.com/k7cfo/remove-your-data/issues/4)): detect tools, use them, or coach. No Python → `templates/paper-log.md`. Missing browser/mail/scheduler degrades; do not refuse the job.
- Localhost dashboard restyle ([#3](https://github.com/k7cfo/remove-your-data/issues/3)): knowsuchagency **Nothing** tokens (instrument panel, red interrupt, `light-dark`, theme toggle). Stdlib CSS only.
- Scheduler ([#2](https://github.com/k7cfo/remove-your-data/issues/2)): detect what this host already uses; recommend one specific re-invoke. Not a catalog of products.
- Stdlib-only QA suite and GitHub Actions matrix for Python 3.10–3.13: CLI, SQLite, consent boundaries, HTTP routes, security headers, exports, and registry parsing. CI uses synthetic data and never contacts a broker.
- Dashboard hardening: same-origin POST checks, DNS-rebinding Host validation, CSP/security headers, safe URL rendering, private export modes, and off-loopback preview restricted to the built-in synthetic demo.

### Changed

- README shots: report, roster, and settings from the Nothing dashboard (dark, sample household).
- Search packs now require a completed primary intake, preserve explicit unconfirmed consent, exclude the defunct Open Data USA host, and report DROP status per person.
- Evidence CSV exports include the complete household chronology, use deterministic ordering, and neutralize spreadsheet formulas.
- `master` is protected: PR required; QA checks `browser-smoke` and `test (3.10)`–`test (3.13)` must be green. Admin bypass is emergency-only ([#9](https://github.com/k7cfo/remove-your-data/issues/9)).

- Whitepages Property Intel escalation ladder: people suppression does not cover `property.whitepages.com`; email `privacyrequest@` with the exact property URL; one substantive Zendesk same-thread follow-up after ~2 business days of silence (not empty ack spam); letter / regulator / attorney packet after ~14–30 calendar days if origin still live. ContactOut: complete verify links from a residential/consumer browser the person controls; escalate letter/regulator if still live after the legal clock — do not loop Turnstile.

- Field notes: ContactOut Turnstile + `support@` fallback; TruePeopleSearch `.net` Google Form needs a signed-in consumer Google; Spokeo empty `/optout` → `privacy@`; Open Data USA null-MX / leftover vehicle cards / letter after the contact window / parked origin cancels the letter (confirm via browser + RDAP); origin timeout is not a drop; PeopleConnect name-index teasers can go quiet then resurface; curl CF vs browser can disagree; hourly CF after a live reading is opacity; Radaris city-only skip; ~90-day re-list clock; Whitepages Zendesk auto-ack may omit California (reply on the same thread); CheckPeople written expunge vs ~48h CF lag, then Google name-index can still snippet PII while origin is CF (do not refile); MyLife 410 can still SERP; National Public Data `/optout.html` Turnstile + `support@` fallback (vendor confirm can cover unique + name-index; watch 24–72h); Whitepages same-thread follow-up can mint a new Zendesk number (treat as same request; do not reply again); MyLife Atlassian support can confirm account + published-profile deletion (3–5 business day purge; origin can 404; watch 24–72h; no SERP while leftover origins live); PeopleConnect name-only confirmation vs separate phone/address criteria (same-thread exact URL follow-up, ~48h); sweep every household number; bare name-index SERP with identifiers counts; Bing datacenter verification via RSS and Yahoo-as-Bing nuance; Sync.me 200/Unknown false positives; reverse-phone SERP can stay stale after origin flips to someone else (clear leftover, do not cite in suppression follow-up); PeopleConnect same-thread residual may extend to phone/address criteria and carve out non-subject numbers; orphan press-Send draft superseded by sent residual → close pending-send, do not recreate/nag; reverse-phone can reattribute from subject to a household relative at the same street/number (clear subject-primary; household leftover may remain; do not restart four-brand PeopleConnect from that alone; PeopleConnect residual auto-ack quoting a processing window ≠ resolution (watch; do not nag during the window); CyberBackgroundChecks `/removal` Turnstile (one attempt); no invent subject PID when only household detail exists)

