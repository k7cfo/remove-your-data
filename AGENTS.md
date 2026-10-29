# AGENTS.md

You are running **remove-your-data**. This repository is the skill. Humans paste the repo URL into a harness; you execute it.

This is not legal advice.

Author: Nick Newsom (@k7cfo). License: Apache-2.0 (see `LICENSE`, `NOTICE`). Forks are welcome; keep `NOTICE`.

## Boot (do this now)

0. **Run `python3 scripts/ryd.py recap --workspace "$WORKSPACE"` first** in every session and after any context loss (once a workspace exists). It is read-only. If it is not in the recap, say "not recorded".
1. Read [`SKILL.md`](SKILL.md) in full. That is the playbook. Do not improvise a parallel process.
2. **§0 capability.** List tools this host already has (`python3`, folder, browser, search, mailbox, scheduler). Do not install software they did not ask for. Missing a tool is not a stop: use what you have, or coach the human (`SKILL.md` §0). Python is optional.
3. If the roster has no primary person, run **SKILL.md §1 intake 1:1** and **stop**. One question per turn. Do not dump the questionnaire. Roster goes in SQLite (`/roster` or `ryd.py`) **or** `templates/paper-log.md`. Do not search until residency is known **and** intake Q9 is done.
4. If they live in California, **CA DROP first** — one request per roster person. Other US states and DC: `attest-residency`, `law-plan`, `law-request`, `law-event` (`SKILL.md` §2). Family members: **household inbox** is the default (file as the person, in their own name, from their own inbox, so verify/OTP links land there); no extra setup. Authorized-agent filing is the alternative (`record-filer --mode authorized-agent`, `SKILL.md` §1). Packs are data checked against primary sources on a stated date, not legal advice.
5. Put the workspace **outside this git clone**. Never commit `takedown.db`, paper logs, evidence, DROP IDs, or listing URLs that identify a real person.
6. After a pass: present results in chat as the generated card (`ryd.py report --image`, plus `report` markdown; `--text` if the host cannot show images). Do not point the user to the dashboard instead. `ryd.py serve` (`/`, `/roster`, `/settings`) is an optional read-only view. Otherwise the paper log is the report. Agents use `ryd.py settings` instead of scraping the page when it exists.

## Tools

Use whatever this host already has. Do not install software they did not ask for. Gap → one offer to get it, then degrade, then coach (`SKILL.md` §0).

| Need | Prefer | Fallback |
| --- | --- | --- |
| Browser / forms | Host browser MCP, Playwright, Puppeteer, Browser Use | Coach the official URL and fields; they click |
| Search | Host web_search first. Then keyless DDG/Brave/Bing/Startpage/Yandex/SearXNG/Google isolated. APIs only if already configured (Exa, Firecrawl, Brave, Tavily). Catalog: `references/search.md`. Google Results about you is last failsafe (§7a), not a broker opt-out. | They paste listing URLs they already see |
| Mail / OTP | AgentMail, else a mailbox they control. Consumer Gmail/Yahoo/Outlook fallback for brokers that reject agent domains | They click verify; never take their password |
| Log / roster / routine | `init` then `/roster` + `/settings`, or `add-person` / `add-ident` / `pack` / `settings` | `templates/paper-log.md` outside the clone |

## Do not

- Pay or recommend Incogni, DeleteMe, Optery, or similar
- Impersonate anyone (household inbox filing for family is fine; file with the person's knowledge)
- Loop Turnstile / datacenter-blocked forms
- Bind the dashboard off `127.0.0.1`
- Put addresses, phones, emails, listing URLs, or request ids in chat reports or cards

## Reporting

Chat is the interface. `recap` first (session start, after context loss); `report --image` to show results as a status card with markdown/text/JSON fallbacks. Cards carry vendor names, statuses, counts, and relative due dates only. Never claim a listing is gone or filed unless the log shows it. Details: `SKILL.md` "Session start and reporting".

## Map

| Path | What |
| --- | --- |
| `SKILL.md` | Playbook (file pass vs verify pass) |
| `STATUS.md` | Broker opt-out status: verified / untested / defunct |
| `references/brokers.md` | Opt-out queue (verify live URLs) |
| `references/dead-urls.md` | Skip without looping; `ryd.py pack` prints these |
| `references/jurisdictions.md` | Legal clocks |
| `laws/` | Versioned US state law packs, `schema.json`, request/appeal templates; `laws/README.md` says how to update one |
| `references/search.md` | Query pack + SERP new-host watch |
| `templates/erasure-request.md` | Letter when there is no form |
| `templates/regulator-complaint.md` | After the legal clock; do not auto-send |
| `templates/paper-log.md` | No-Python workspace (roster, CSV log, clocks) |
| `docs/PRIVACY.md` | What leaves the machine |
| `scripts/schema.sql` | Legal log schema (`relist_90d`, roster `keep_host` / `keep_url`) |
| `scripts/ryd.py` | `init` / `serve` / `export` / `add-person` / `add-ident` / `pack` / `settings` / `recap` / `report` / `law-validate` / `record-filer` / `attest-residency` / `law-plan` / `law-request` / `law-event` |
| `scripts/ryd_laws.py` | Law pack loader, validator, pack selection, receipt-date clocks, request rendering |
| `scripts/ryd_report.py` | Privacy-safe card model and renderers for `recap` / `report` (md, text, json, PNG) |
| `scripts/registry_pull.py` | CA registry CSV hostname diff — not a spray list |
| `CONTRIBUTING.md` | How to PR |
| `CHANGELOG.md` | What shipped |

`ryd.py` is stdlib-only. Do not add a dependency without a PR that says why. The skill still runs without Python (`SKILL.md` §0).

## Code Review Rules

- Treat consent and completed intake as data boundaries: no search pack or filing may include an inactive, unconfirmed, or intake-incomplete person.
- Keep real PII outside the clone and keep the dashboard loopback-only by default; flag changes that expose workspace data, weaken browser-origin checks, or relax file permissions.
- Keep `ryd.py` and its tests Python-stdlib-only unless a PR explicitly justifies a dependency. Deterministic checks belong in CI; live broker forms and real identities do not.
