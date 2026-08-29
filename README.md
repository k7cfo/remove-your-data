# remove-your-data

![Takedown dashboard](docs/dashboard.png)

A skill for coding agents (Claude, Codex, Pi, OMP, Hermes, OpenClaw, and anything else that loads `SKILL.md`) that takes down people-search listings and data-broker records **without paying deletion services**.

Free to use. Copyleft. One canonical repo.

This is not legal advice.

## Why this exists

Data brokers publish you. Paid "we'll delete you" apps mostly file the same free opt-outs, then charge rent because the brokers re-scrape. Some of those brands sit next to the people-search business. This skill is the first-party path: your rights, official forms, a legal log, a repeating clock.

## Canonical repo — please do not publish a fork

GitHub turns on forks for every public repository. That button cannot be disabled here. **Do not use it as a publishing model.**

- Use a fork only as a short-lived GitHub mechanic to send a **pull request**.
- Do not advertise, package, or maintain a diverging copy.
- If you improved a broker URL, a jurisdiction clock, or a captcha workaround, open a PR against **this** repository so everyone gets it.

Published modifications are covered by the AGPL (see License). That is how improvements can be pulled back here even if someone ignores this request.

This project will not list or endorse downstream forks.

## License

[GNU Affero General Public License v3.0 or later](LICENSE).

- You may run it, copy it, and share it at no charge.
- If you distribute a modified version, it must stay AGPL and include source.
- If you run a modified version as a **network service** (hosted "delete my data" agent, SaaS wrapper, paid removal bot), AGPL §13 requires you to offer that modified source to its users. Do not wrap this skill as a paid deletion product and keep the changes.

Inbound = outbound: contributions are AGPL-3.0-or-later. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Install (drop the folder in)

Copy `SKILL.md` plus `references/`, `scripts/`, and `templates/` into the host's skills directory. Names vary:

| Host | Typical path |
| --- | --- |
| Claude Code | `.claude/skills/remove-your-data/` |
| Codex | `.codex/skills/remove-your-data/` or the host's skill loader |
| Pi / OMP | the environment's `skills/remove-your-data/` |
| Hermes / OpenClaw | `skills/remove-your-data/` |
| Grok | `~/.grok/skills/remove-your-data/` |

Point the agent at this skill ("remove my data from people-search sites"). First run is intake questions. California residents get DROP first.

**Never put the person's PII workspace inside this git clone.** The agent creates `takedown.db` and `evidence/` somewhere else.

## What the agent does

1. Asks who you are, where you live, how often to re-check, and how anonymous to be.
2. If you live in California: [CA DROP](https://privacy.ca.gov/drop/) first, then public people-search opt-outs.
3. Searches multiple engines (browser, keyless, or Exa/Firecrawl/Brave/etc. if you already have them).
4. Files official free opt-outs. Completes email/OTP via AgentMail or a mailbox you control.
5. Keeps a SQLite legal log and a localhost HTML running report.
6. Re-runs on the cadence you set, because listings come back.

## Dashboard

Python 3.10+, stdlib only. The log lives **outside** this clone.

```bash
python3 scripts/ryd.py init --workspace "$HOME/privacy-takedown"
python3 scripts/ryd.py serve --workspace "$HOME/privacy-takedown"
# http://127.0.0.1:8765/

python3 scripts/ryd.py export --workspace "$HOME/privacy-takedown"
python3 scripts/ryd.py export-csv --workspace "$HOME/privacy-takedown"

# Fake data, for a look at the UI:
python3 scripts/ryd.py serve --demo
```

Loopback only. It will refuse `0.0.0.0`. Listings, legal clocks, leftovers, mail, and evidence chronology. Refreshes every 30 seconds. `?hero=1` is a tighter frame for screenshots.

## Requirements on the machine

- Python 3.10+ and `sqlite3` (stdlib + CLI)
- A browser the agent can drive (the host's browser tool, Playwright, Puppeteer, or similar)
- A mailbox the agent or you can read (AgentMail recommended; Gmail/Yahoo/Outlook fallback for brokers that reject custom domains)

## Community

The broker list and jurisdiction clocks go stale. That is the work.

Useful PRs: dead opt-out URLs, new official forms, DROP/GDPR clock corrections, captcha/mailbox gotchas, search queries that actually find listings, scheduler notes for a specific agent host.

Not useful: paid-service affiliate links, "just use Incogni," or a rewrite that stores PII in the skill repo.
