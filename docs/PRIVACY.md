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
- The localhost dashboard binds `127.0.0.1` only.

## Roster allowlist

Hosts and URLs the person wants **kept** (LinkedIn, news, personal site, interviews) live on the roster as `keep_host` / `keep_url`. They are not search identifiers. Never file an opt-out or SERP hide against an allowlisted host or URL.

Default even without roster rows: skip articles, LinkedIn, and other non-broker coverage.

## Paid removal brands

Do not send data to Incogni, DeleteMe, Optery, or similar. Do not recommend them.
