# Privacy / data flow

This skill files **the person's own** opt-outs. It is not a telemetry product. This is not legal advice.

## What leaves the machine

Only what an official form, letter, or regulator already needs:

- Official opt-out forms and privacy portals (name as listed, listing URL, the identifiers **already on that listing**, plus whatever that form requires).
- The person's mailbox (verify links, OTP, broker replies). Prefer a dedicated inbox; see `SKILL.md` §4.
- California DROP / Login.gov or Identity Gateway, when they are a CA resident and choose to file.
- Search queries used to find **their** listings (name + city, or name + street). Minimum set. No full-identifier dump into a third-party search API unless they said yes (`anonymity_mode=max` forbids it).
- Google/Bing index failsafes, last, on **their** search account — not the agent's (`SKILL.md` §7a).
- A regulator or attorney packet they asked you to export (`exports/evidence-log.csv`).

Do not volunteer DOB, SSN, extra phones, or ID scans unless that form requires them.

## What does not leave

- No telemetry from this skill. `ryd.py` does not phone home.
- The git clone of this repo stays free of PII. Never commit `takedown.db`, paper logs, evidence, DROP IDs, listing slugs, phones, emails, or ticket numbers.
- The workspace (`takedown.db` or `templates/paper-log.md` copies, `evidence/`, `exports/`) lives **outside** the clone. `chmod 700` workspace, `chmod 600` db if you have one.
- Confirm pages, request IDs, DROP IDs, and mailbox contents stay in that private workspace (`action_log`, paper log, `email_event`, `evidence/YYYY-MM-DD/`).
- A real-data dashboard binds `127.0.0.1` only. `RYD_PREVIEW=1` can bind off loopback only with the built-in synthetic `--demo` workspace.

The SQLite workspace is not application-encrypted. Keep it on an encrypted, non-synced disk or encrypted home directory when the identifiers are sensitive.

## Privacy landscape

`/landscape?p=<person_id>` counts only that person's listings recorded in the local workspace. The default selection matches the report; an unknown person ID shows an empty view. This is not comprehensive internet exposure or a map of the subject's home, IP address, servers, or data centers.

- `broker.operator_region` is explicit, manually curated metadata: `NA`, `SA`, `EU`, `AF`, `AS`, `OC`, or `UNKNOWN`. Leave it `UNKNOWN` unless the operator's coarse region is known. Do not infer it from a name, domain suffix, subject residency, or network lookup. A listing without a broker also stays Unknown.
- To record a known region, update that broker's `operator_region` in the private workspace database using its broker ID. Keep the source/rationale in `broker.notes`; notes never enter the visualization payload. No region lookup or enrichment is performed by the page.
- SQLite triggers append `listing_status_event` on listing insertion and actual status changes, including direct SQL writes. These are local recording timestamps, independent of `created_at_utc` and `updated_at_utc`; `action_log` remains the legal evidence log.
- `init` and `serve` upgrade existing workspaces with one migration-time baseline per listing lacking events. Earlier transitions are not invented. Read-only access before migration still shows current counts as Unknown, with no history.
- History is ordered by UTC instant and event ID. Simultaneous events produce one frame; the last event ID determines each listing's state at that instant. Every status except `gone` remains exposed, including blocked listings. Re-listing increases exposure again.
- Historical frames use the operator regions assigned now. Current is a separate snapshot at page load. The page does not refresh or perform live checks.

The embedded visualization JSON contains only timestamps, exposed/gone counts, and coarse region codes—no names, identifiers, person/listing/broker IDs, URLs, request IDs, notes, or evidence. The surrounding page still contains the selected name and household navigation: keep the entire page private even though its visualization payload is aggregate-only.

The simplified SVG, styles, and timeline script are inline. No geolocation, DNS, WHOIS, external tiles, webfonts, telemetry, or background network requests. Playback starts paused. Native buttons and the range slider support keyboard operation; reduced motion disables timed playback while preserving manual scrubbing. With JavaScript off, the current globe, totals, and seven-region table remain available.

## Roster allowlist

Hosts and URLs the person wants **kept** (LinkedIn, news, personal site, interviews) live on the roster as `keep_host` / `keep_url`. They are not search identifiers. Never file an opt-out or SERP hide against an allowlisted host or URL.

Default even without roster rows: skip articles, LinkedIn, and other non-broker coverage.

## Paid removal brands

Do not send data to Incogni, DeleteMe, Optery, or similar. Do not recommend them.
