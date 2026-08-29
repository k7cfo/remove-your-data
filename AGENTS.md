# AGENTS.md

You are running **remove-your-data**. This repository is the skill. Humans paste the repo URL into a harness; you execute it.

This is not legal advice.

## Boot (do this now)

1. Read [`SKILL.md`](SKILL.md) in full. That is the playbook. Do not improvise a parallel process.
2. If there is no complete intake in the workspace database, run **SKILL.md §1** (questionnaire) and **stop**. Do not search or file until residency is known.
3. If they live in California, **CA DROP first**, then public people-search opt-outs.
4. Put the SQLite workspace **outside this git clone**. Never commit `takedown.db`, evidence, DROP IDs, or listing URLs that identify a real person.
5. After a pass: `python3 scripts/ryd.py serve --workspace "$WORKSPACE"` (loopback only) and/or `export`.

## Tools

Use whatever this host already has. Do not install software they did not ask for.

| Need | Prefer |
| --- | --- |
| Browser / forms | Host browser MCP, Playwright, Puppeteer, Browser Use |
| Search | Host web_search, then keyless DDG/Brave/SearXNG, then Exa/Firecrawl/Brave API if already configured |
| Mail / OTP | AgentMail, else a mailbox they control. Consumer Gmail/Yahoo/Outlook fallback for brokers that reject agent domains |
| Log | `python3 scripts/ryd.py init --workspace …` then SQLite |

## Do not

- Pay or recommend Incogni, DeleteMe, Optery, or similar
- Impersonate anyone
- Loop Turnstile / datacenter-blocked forms
- Bind the dashboard off `127.0.0.1`
- Publish a fork of this skill. Open a **pull request on this repo**. Broker URLs and clocks go stale; PRs are how it stays good.

## Map

| Path | What |
| --- | --- |
| `SKILL.md` | Playbook |
| `references/brokers.md` | Opt-out queue (verify live URLs) |
| `references/jurisdictions.md` | Legal clocks |
| `references/search.md` | Query pack |
| `templates/erasure-request.md` | Letter when there is no form |
| `scripts/schema.sql` | Legal log schema |
| `scripts/ryd.py` | `init` / `serve` / `export` / `export-csv` |
| `CONTRIBUTING.md` | How to PR |

Python is stdlib-only. Do not add a dependency without a PR that says why.
