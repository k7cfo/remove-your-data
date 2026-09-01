# AGENTS.md

You are running **remove-your-data**. This repository is the skill. Humans paste the repo URL into a harness; you execute it.

This is not legal advice.

## Boot (do this now)

1. Read [`SKILL.md`](SKILL.md) in full. That is the playbook. Do not improvise a parallel process.
2. **§0 capability.** List tools this host already has (`python3`, folder, browser, search, mailbox, scheduler). Do not install software they did not ask for. Missing a tool is not a stop: use what you have, or coach the human (`SKILL.md` §0). Python is optional.
3. If the roster has no primary person, run **SKILL.md §1 intake 1:1** and **stop**. One question per turn. Do not dump the questionnaire. Roster goes in SQLite (`/roster` or `ryd.py`) **or** `templates/paper-log.md`. Do not search until residency is known **and** intake Q9 is done.
4. If they live in California, **CA DROP first** — one request per roster person.
5. Put the workspace **outside this git clone**. Never commit `takedown.db`, paper logs, evidence, DROP IDs, or listing URLs that identify a real person.
6. After a pass: `ryd.py serve` if Python works (report `/`, roster `/roster`, settings `/settings`). Otherwise the paper log is the report. Agents use `ryd.py settings` instead of scraping the page when it exists.

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
- Impersonate anyone
- Loop Turnstile / datacenter-blocked forms
- Bind the dashboard off `127.0.0.1`
- Publish a fork of this skill. Open a **pull request on this repo**. Broker URLs and clocks go stale; PRs are how it stays good.

## Map

| Path | What |
| --- | --- |
| `SKILL.md` | Playbook (file pass vs verify pass) |
| `STATUS.md` | Broker opt-out status: verified / untested / defunct |
| `references/brokers.md` | Opt-out queue (verify live URLs) |
| `references/dead-urls.md` | Skip without looping; `ryd.py pack` prints these |
| `references/jurisdictions.md` | Legal clocks |
| `references/search.md` | Query pack + SERP new-host watch |
| `templates/erasure-request.md` | Letter when there is no form |
| `templates/regulator-complaint.md` | After the legal clock; do not auto-send |
| `templates/paper-log.md` | No-Python workspace (roster, CSV log, clocks) |
| `docs/PRIVACY.md` | What leaves the machine |
| `scripts/schema.sql` | Legal log schema (`relist_90d`, roster `keep_host` / `keep_url`) |
| `scripts/ryd.py` | `init` / `serve` / `export` / `add-person` / `add-ident` / `pack` / `settings` |
| `scripts/registry_pull.py` | CA registry CSV hostname diff — not a spray list |
| `CONTRIBUTING.md` | How to PR |
| `CHANGELOG.md` | What shipped |

`ryd.py` is stdlib-only. Do not add a dependency without a PR that says why. The skill still runs without Python (`SKILL.md` §0).

## Code Review Rules

- Treat consent and completed intake as data boundaries: no search pack or filing may include an inactive, unconfirmed, or intake-incomplete person.
- Keep real PII outside the clone and keep the dashboard loopback-only by default; flag changes that expose workspace data, weaken browser-origin checks, or relax file permissions.
- Keep `ryd.py` and its tests Python-stdlib-only unless a PR explicitly justifies a dependency. Deterministic checks belong in CI; live broker forms and real identities do not.
