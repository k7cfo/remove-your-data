---
name: remove-your-data
license: AGPL-3.0-or-later
description: >
  Remove a person's personal information from people-search sites and data
  brokers worldwide without paying deletion services. Use when the user wants
  to delete their data, opt out of data brokers, file California DROP, exercise
  GDPR / UK GDPR erasure, take down Spokeo Whitepages Radaris BeenVerified
  TruePeopleSearch listings, stop using Incogni DeleteMe Optery, run a
  recurring privacy takedown, or make data removal anonymous. First run MUST
  ask intake questions. If they live in California, use CA DROP first.
---

# Remove your data

Free, first-party takedown of people-search listings and data-broker records.
Log every step so a regulator, letter service, or attorney can use it later.

This is an operations playbook, not legal advice.

Canonical repo: https://github.com/k7cfo/remove-your-data — send improvements as PRs, do not publish a fork. Boot: `AGENTS.md`.

## About and why

Data brokers collect, scrape, and sell names, phones, addresses, relatives, and inferred profiles. People-search sites publish that dossier to anyone who types a name.

Paid "delete my data" services (Incogni, DeleteMe, Optery, and the rest) mostly submit the same free opt-out forms this skill files, then charge a subscription because brokers **re-scrape and re-list**. Recurrence is the product.

The conflict is structural:

- The industry that publishes you also sells the mop.
- PeopleConnect owns Intelius, TruthFinder, Instant Checkmate, and US Search — they sell the reports and run the suppression center.
- Some people-search companies historically sold both access to your record and a paid way to hide it.
- Even when the removal brand is a separate company, it profits while the leak stays open. You paying them does not bind the broker to a higher standard than the free legal request.

This skill does not pay those services. It exercises the person's own rights (CA DROP, CCPA/CPRA, GDPR Art. 17, and the site's official opt-out), keeps a legal log, and repeats on a clock because listings come back.

If they already pay a removal service: do not buy more. Do not blindly re-file every private broker it claims to cover. Still file the **public indexed** people-search sites yourself — those are what Google shows, and paid plans often leave them up.

## Hard rules

- Do not start searching or filing until first-run intake is complete, especially residency.
- If they live in California, run CA DROP before grinding public forms.
- Do not impersonate a spouse, child, or anyone else. Use the site's family / authorized-agent option only when it exists and they asked.
- Do not opt out other-state / other-country people who share the same name.
- Do not collect anyone's email or site password. If a verify link lands in a mailbox you must not open, they click it.
- Do not retry Cloudflare Turnstile / datacenter-blocked forms in a loop. Log `blocked`, move on.
- Do not reuse one email on sites that enforce one address per person (Open Data USA does this and normalizes Gmail plus-aliases).
- Do not promise a listing is gone because a confirm page said so. Recheck the public URL.
- Do not store the person's PII in this skill repo, in git, or in chat logs you cannot control. Workspace is a separate directory.
- Do not recommend paying Incogni / DeleteMe / Optery / similar. If a site demands payment to opt out, it is an upsell — use the official free form or a legal request.
- One clean filing plus verify per listing. Recheck later instead of spamming the form.

## 1. First run — ask, then stop

On the first invocation for a person, ask these in **one** questionnaire. Do not search until they answer at least name, residency, and contact path. Ask follow-ups only for blanks.

Required:

1. Legal name, and every alias / maiden / nickname they want covered.
2. **Where they live right now** — country, and if US / Canada / Australia the state or province. If they say California, DROP is first.
3. Current city and postal / ZIP. Street address only if they want address-level matching (needed for DROP and most people-search opt-outs).
4. Mobile number shown on listings, if any.
5. A mailbox they can actually open for verify links and OTP codes (see Email).
6. Cadence: how often should the agent re-scan? Default **every 7 days**. Offer 24h / 7d / 30d / 90d. Legal clocks can fire sooner than this.
7. Scope: just them, or household members on the same street / same phone? Default: them only.
8. Anonymity: `dedicated` (default), `personal`, or `max`. See Anonymity.
9. What this agent can already use: browser (Playwright, Puppeteer, OMP/Chromium MCP, Browser Use, …), search APIs (Exa, Firecrawl, Brave, Tavily, …), email (AgentMail, Gmail IMAP, …). Detect tools yourself, then confirm.

Optional — only if they want broader matching or a form requires it:

- Prior addresses and phones
- Work email (professional / registry leftovers)
- Date of birth (CA DROP and some portals; do not ask up front otherwise)
- MAID / CTV ID / VIN (CA DROP optional identifiers)

Confirm they want **you** to file as their agent using the identifiers they provided, not as a pretend identity.

Write answers into SQLite (`person`, `identifier`, `config`). Set `intake_complete=1`. Then route.

## 2. Jurisdiction router

Pick the primary legal track from residency. Always still do public people-search opt-outs — registries do not remove Google-indexed profile pages.

| Residency | First move | Clock |
| --- | --- | --- |
| California | [CA DROP](https://privacy.ca.gov/drop/) then public opt-outs | Brokers process DROP at least every 45 days; status may take 90 days. CCPA deletion otherwise 45 days (+45). |
| Other US with a consumer privacy law (CO, CT, VA, TX, OR, …) | State deletion / opt-out-of-sale request + public opt-outs. Check that state's portal or AG privacy page. TX / OR / VT also have data-broker **registries** (not a one-shot DROP). | Usually 45 days. Confirm on the state site. |
| Vermont | Registry lookup + individual broker requests | Per broker / VT law |
| EU / EEA | GDPR Art. 17 erasure to each controller | 1 month, extendable to 3 months with notice |
| UK | UK GDPR erasure | 1 month, extendable |
| Canada | PIPEDA access/deletion to each institution | ~30 days |
| Australia | APP access/correction/deletion | ~30 days |
| Anywhere else | Official opt-out forms + any local statute they name | Site-stated window; if none, 30 days |

Load `references/jurisdictions.md` when present.

California extras (do these first, in order):

1. DROP at [consumer.drop.privacy.ca.gov](https://consumer.drop.privacy.ca.gov/) — one request to 600+ registered brokers.
2. Public people-search opt-outs (Spokeo, Whitepages, TruePeopleSearch, …). DROP does not replace these.
3. Recheck DROP status at [consumer.drop.privacy.ca.gov/dropstatus](https://consumer.drop.privacy.ca.gov/dropstatus).

DROP does **not** delete first-party accounts the person created themselves, exempted data, or some publicly available records. People-search pages can still rank. File them.

## 3. Workspace and legal log

Create a workspace **outside** this repo (PII never belongs in git):

```text
$WORKSPACE/
  takedown.db          # SQLite source of truth
  evidence/YYYY-MM-DD/ # screenshots, raw confirm pages, .eml
  exports/             # CSV / JSON dumps for a lawyer
```

Init:

```bash
python3 scripts/ryd.py init --workspace "$WORKSPACE"
```

(`scripts/schema.sql` is applied for you. chmod 700 workspace, 600 db.)

SQLite beats CSV as the system of record: unique listing URLs, due-date queries, request IDs, joins across person / broker / clock / email. CSV is an **export**, not the database.

On every real action insert `action_log` with:

- `occurred_at_utc` and `occurred_at_local` (person's timezone from intake)
- actor (`agent`, `user`, `family`)
- broker, listing URL, action, channel, request ID, result
- path to evidence file

After each filing, insert or refresh a `clock` row (verify email, site drop window, legal response, DROP 45/90).

Export when asked, or before escalation:

```bash
sqlite3 -header -csv "$WORKSPACE/takedown.db" \
  "SELECT * FROM v_evidence_chronology ORDER BY occurred_at_utc" \
  > "$WORKSPACE/exports/evidence-log.csv"
```

Keep leftovers in table `leftover` (and optionally `exports/leftovers.md`): URL, what PII is still shown, how you found it, where it is stuck, next step.

After each pass, refresh the running report:

```bash
python3 scripts/ryd.py serve --workspace "$WORKSPACE"
# http://127.0.0.1:8765/  — loopback only
python3 scripts/ryd.py export --workspace "$WORKSPACE"
```

Tell the person the dashboard URL. Do not bind it off localhost. On DROP submit, also `INSERT OR REPLACE INTO config(key,value) VALUES ('drop_filed','1')` so the report shows DROP as filed (store the DROP ID in `action_log.request_id`, not in git).

## 4. Email and 2FA

Brokers send confirmation links and OTP codes. The agent cannot finish filings without a mailbox.

Prefer this order:

1. **AgentMail** ([https://agentmail.to](https://agentmail.to), console [https://console.agentmail.to](https://console.agentmail.to), docs [https://docs.agentmail.to](https://docs.agentmail.to)) — dedicated inbox the agent can read (API / MCP). Suggest creating one on first run if they have none. Coding-agent setup: [Give your coding agent an email inbox](https://www.agentmail.to/blog/give-your-coding-agent-an-email-inbox).
2. If they refuse AgentMail: connect **read-only** access to a mailbox they control (IMAP, Gmail API, or the host's email MCP). Not their password pasted into chat.
3. **Consumer fallback inbox** (Gmail, Yahoo, or Outlook) that is **not** their daily-driver. Required because Spokeo and Open Data USA reject many custom / agent domains, and Open Data USA normalizes Gmail `+` aliases. Keep one real Gmail/Yahoo/Outlook for those sites only.

Store which mailbox was used per listing (`email_used`). Never reuse a one-per-person address across two people.

When a verify email arrives: fetch it, extract the link or code, complete the flow, log `email_event`, recheck the public URL the same day.

If the code went to a personal inbox you cannot read: tell them the exact subject / sender to look for (including spam). Do not ask for the account password.

## 5. Anonymity

Goal: the takedown does not create a *new* dossier.

Default `dedicated`:

- Isolated browser profile. Not logged into Google, Facebook, Apple, or their daily accounts.
- Dedicated mailbox (AgentMail + one consumer fallback). Not the email printed on their resume.
- Workspace dir `chmod 700`, db `chmod 600`, never committed.
- Send each broker only the identifiers already on that listing, plus whatever the form requires. Do not volunteer DOB, SSN, or extra phones.
- Search queries are the minimum to find **their** listing (name + city, or name + street). Do not dump the full identifier set into one third-party search-API call.

`personal`: allowed to use their real email and a logged-in browser when a site demands it (Whitepages phone-verify, Login.gov for DROP). Still keep the SQLite workspace private.

`max` (harder, some filings will fail):

- Isolated profile + prefer residential / non-datacenter IP. Datacenter IPs get Turnstile / 403 on TruePeopleSearch, FastPeopleSearch, Whitepages.
- Prefer keyless / self-hosted search (SearXNG, DuckDuckGo HTML, browser against the search engine). Do not send the person's name to Exa / Tavily / SerpAPI if they refused third-party search.
- Do not paste identifiers into a cloud LLM dashboard they do not already trust. Run this skill in their local agent.
- No household filings, no extra identifiers.
- AgentMail is fine; consumer Gmail links the person. For `max`, expect some brokers to reject AgentMail — log `blocked: mailbox rejected` instead of falling back unless they authorize it.

DROP residency verify is inherently identifying (California Identity Gateway or Login.gov). For CA residents, that is the point. You cannot complete Login.gov 2FA for them — hand them the session at the sign-in page. They cannot switch verify methods after they pick one. A regular myDMV login is not Identity Gateway.

VPN: optional. If captchas explode, try without VPN or a residential path. Do not hammer.

## 6. Search stack

Detect what this host already has. Do not install software they did not ask for.

### Browser (for forms, JS, captchas)

Prefer a real browser over `curl`. People-search opt-outs are JS, email-verify, and bot-walled.

Pick the first that exists:

1. **This agent's native browser** — OMP Chromium / chrome-devtools MCP, Pi/Hermes browser, Codex/Claude browser. Drive it like a user: open the official opt-out, snapshot the page, fill, evidence-screenshot.
2. **Playwright** or **Puppeteer** in an isolated profile.
3. **Browser Use** / Stagehand / similar CDP harness.

OMP-style pattern (adapt to whatever tool names this host exposes): open the URL, wait for DOM, take an accessibility snapshot, act on the form, screenshot the confirmation, save that file under `evidence/`. Do not fake a successful opt-out from a curl of the homepage.

If the form is Turnstile-blocked from this IP: one attempt, log `blocked`, leftover it. Do not loop.

### Finding listings

Run the same query pack across **several** engines. One index is not enough; people-search mirrors diverge.

Query pack (every identifier they authorized):

```text
"Legal Name" "City"
"Legal Name" "Street"
"Legal Name" "Region"
"Alias" "City"
"Phone with dashes"
"Phone digits only"
"Name" site:spokeo.com
"Name" site:whitepages.com
"Name" site:radaris.com
"Name" site:truepeoplesearch.com
"Name" site:beenverified.com
```

Engine / API preference (use what exists, skip the rest):

| Kind | Tools | Use for |
| --- | --- | --- |
| Keyless / low-key | DuckDuckGo HTML, Brave Search UI, Startpage, Bing UI, Mojeek, Qwant, SearXNG (self-host or public instance), Google UI in the isolated browser | Default discovery. Browser-drive Google/Brave/DDG if no API. |
| Agent search APIs | **Exa** (semantic: "people search profile for Name in City"), **Firecrawl** (search + scrape the listing page to markdown), Brave Search API, Tavily, Parallel, Linkup, Perplexity | Fast recall when the user already has a key or a free tier. |
| SERP APIs | Serper, SerpAPI, SearchAPI, ScrapingDog | Google-like result pages. Optional. |
| URL to text | Jina `r.jina.ai/{url}`, Firecrawl scrape | Evidence capture when the browser is overkill. |
| Native host search | OpenClaw/Hermes web_search, OMP web_search, Claude/Codex web search | Use first if the host already searched the web for you. |

Keyless path when there are **no** search keys: isolated browser → DuckDuckGo, Brave, Bing, Google (in that order if one is captcha-walled), plus site-search on the broker list in `references/brokers.md`.

Also search the phone in reverse-lookup teasers. A paywall that hides the name is a leftover, not a free opt-out target, unless an official removal form still accepts the URL.

When a URL matches this person (same phone, street, or city — not just the same name in another state): insert `listing` **before** filing.

Load `references/search.md` when present.

## 7. File free opt-outs

Official form only. Prefer email-verify flows you can complete. Solve captchas if they authorized that.

Load `references/brokers.md` and treat it as a **queue**, not gospel. Opt-out URLs rot — verify the live privacy /opt-out page before submitting. Send URL fixes upstream.

Priority order:

1. Listings already ranking for their name (from the search pass).
2. High-visibility public sites: Whitepages, Spokeo, BeenVerified, TruePeopleSearch, FastPeopleSearch, Radaris, Open Data USA.
3. PeopleConnect suppression center once — covers Intelius, TruthFinder, Instant Checkmate, US Search.
4. Upstream wholesalers (Acxiom, LexisNexis people-search opt-out) even if they do not rank.
5. Everything else in `references/brokers.md` that matched.

Per listing:

1. Snapshot the public page (screenshot + URL + what PII is shown).
2. File the official opt-out. Save request ID / tracking UUID.
3. Complete email or phone verify.
4. Insert `clock` for the site's stated window (Spokeo often 24–48h; otherwise 7 days, then the legal clock).
5. Recheck the **exact** listing URL. 404 / "we couldn't find this profile" = success. Property and reverse-phone URLs that still tease the household are separate rows.

Site notes that keep biting:

- **Spokeo** — profile or `/optout`. Keep `optout_request_id`. Uncommon domains (including some AgentMail) are rejected; use the consumer fallback inbox.
- **Open Data USA** — one email per person; Gmail `+` aliases collapse; custom domains often rejected. Quoted-printable mail can corrupt `token=` (`=11` → control char); reconstruct from the raw `.eml` if the link 404s. Confirm page can lie; recheck the public URL.
- **Radaris** — official privacy form; confirm email required. Name-index URL and regional mirrors can both stay live. Recheck both.
- **Whitepages** — suppression form; often an automated **phone call** with a code. Have them ready. Old addresses = extra profiles.
- **PeopleConnect** — one suppression for the family. Do not file Intelius / TruthFinder / Instant Checkmate / US Search separately unless a listing remains.
- **TruePeopleSearch / FastPeopleSearch** — same operator family; file both. Datacenter 403 is common.

If a site has no form: send `templates/erasure-request.md` to the privacy contact, start a legal clock, log the message-id.

## 8. California DROP

Only if they are a California resident (or filing for one with a permitted authorized-agent path).

Official: [https://privacy.ca.gov/drop/](https://privacy.ca.gov/drop/)
App: [https://consumer.drop.privacy.ca.gov/](https://consumer.drop.privacy.ca.gov/)
How it works: [https://privacy.ca.gov/drop/how-drop-works/](https://privacy.ca.gov/drop/how-drop-works/)
Registry: [https://cppa.ca.gov/data_broker_registry/](https://cppa.ca.gov/data_broker_registry/)

Rules:

- One person per DROP request. Do not add a spouse on the same request.
- Verify via California Identity Gateway (no account) or existing Login.gov. Hand them the computer for Login.gov 2FA. They cannot switch methods later.
- Fill every identifier they already gave for themselves. More data = more matches. Optional: MAID, CTV ID, VIN.
- After submit, log the **8-digit DROP ID**, Pacific time, and UTC. Do not paste the DROP ID into public issues or this git repo.
- Brokers must process at least every 45 days (started 1 Aug 2026). Status can take up to 90 days.
- Status meanings: Deleted, Exempted, Opted-out (no exact match — they still hold data but cannot sell/share), Record not found, Pending.
- They can add identifiers later via DROP status → profile. They cannot use DROP to wipe a first-party account they created at a business.

DROP is ongoing, not one-shot. Keep a `clock` for 45-day recheck and 90-day status.

## 9. Scheduler / agent loop

This is not a one-sitting job. Listings reappear. Laws give brokers weeks.

On first run, persist `cadence_hours` (default 168). Register a recurring job on **whatever this host already has** — do not invent a daemon:

- OpenClaw / Hermes / similar: cron or heartbeat that re-invokes this skill
- systemd user timer, launchd, Task Scheduler
- The host agent's scheduled tasks
- If the host has no scheduler: tell them the exact command / phrase to re-run, and the next due date

Each invocation:

```text
if intake incomplete → section 1
process due `clock` rows (overdue first)
check mailboxes for verify / OTP
recheck listing URLs whose window elapsed
if scan is due by cadence → search pack (section 6)
file new matches (section 7)
CA: if DROP status due → check DROP
export evidence if anything changed
refresh dashboard (`ryd.py export` and/or keep `ryd.py serve` running)
report: gone / pending / leftover / overdue legal clocks
```

Clock kinds:

| kind | when to set | when it fires |
| --- | --- | --- |
| `verify_email` | after filing | every 4–12h until clicked or 7d |
| `site_window` | after verify | site-stated (else 7d) |
| `legal_response` | GDPR/CCPA/letter | 30d or 45d from send; warn at 7d before |
| `drop_45d` | after DROP submit | every 45d |
| `drop_90d` | after DROP submit | once at 90d |
| `rescan` | always | `cadence_hours` |

A listing becomes `gone` only when the exact URL no longer shows the identifier. Verified filing + still visible after the window → `leftover`.

Escalation, unless they say otherwise:

1. Official free path through the stated window
2. Written erasure request (`templates/erasure-request.md`) with the leftovers file
3. State AG / DPA complaint, or attorney, using `exports/evidence-log.csv`

## 10. Household vs same name

- Same street or same phone, and they asked: file if the form is easy (family-member option, no extra identity theater).
- Same name, other region, no matching phone or street: leave it.
- Professional / SoS / LinkedIn cards on a people-search site: file if the card reprints a **home** phone or **home** address. Skip generic company pages.

## 11. Done (one pass)

A pass is done when:

- Intake is in SQLite.
- `ryd.py export` snapshot is current, or `ryd.py serve` is running on loopback.
- CA residents: DROP submitted and DROP ID logged, or they refused DROP in writing in the log.
- Every found public listing is gone, pending inside its window, blocked with a leftover, or leftover with a next step.
- Evidence log is current.
- Recurring job is registered, or they have the next due date.
- No paid removal service was purchased.

Then wait for the next cadence. The work is the loop.
