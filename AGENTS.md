# AGENTS.md

You are running **remove-your-data**. This repository is the skill. Humans paste the repo URL into a harness; you execute it.

This is not legal advice.

## Boot (do this now)

1. Read [`SKILL.md`](SKILL.md) in full. That is the playbook. Do not improvise a parallel process.
2. If the roster has no primary person, run **SKILL.md §1** and **stop**. Aliases/addresses/phones/family go in SQLite (`/roster` or `ryd.py add-ident` / `add-person`). Do not search until residency is known.
3. If they live in California, **CA DROP first** — one request per roster person.
4. Put the SQLite workspace **outside this git clone**. Never commit `takedown.db`, evidence, DROP IDs, or listing URLs that identify a real person.
5. After a pass: `python3 scripts/ryd.py serve --workspace "$WORKSPACE"` (report `/`, roster `/roster`, settings `/settings`). Gear changes cadence/pause; agents use `ryd.py settings` instead of scraping the page.

## Tools

Use whatever this host already has. Do not install software they did not ask for.

| Need | Prefer |
| --- | --- |
| Browser / forms | Host browser MCP, Playwright, Puppeteer, Browser Use |
| Search | Host web_search first. Then keyless DDG/Brave/Bing/Startpage/Yandex/SearXNG/Google isolated. APIs only if already configured (Exa, Firecrawl, Brave, Tavily). Catalog: `references/search.md`. Google Results about you is last failsafe (§7a), not a broker opt-out. |
| Mail / OTP | AgentMail, else a mailbox they control. Consumer Gmail/Yahoo/Outlook fallback for brokers that reject agent domains |
| Log / roster / routine | `init` then `/roster` + `/settings`, or `add-person` / `add-ident` / `pack` / `settings` |

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
| `docs/PRIVACY.md` | What leaves the machine |
| `scripts/schema.sql` | Legal log schema (`relist_90d`, roster `keep_host` / `keep_url`) |
| `scripts/ryd.py` | `init` / `serve` / `export` / `add-person` / `add-ident` / `pack` / `settings` |
| `scripts/registry_pull.py` | CA registry CSV hostname diff — not a spray list |
| `CONTRIBUTING.md` | How to PR |
| `CHANGELOG.md` | What shipped |

Python is stdlib-only. Do not add a dependency without a PR that says why.
