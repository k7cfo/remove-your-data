# Contributing

PRs on this repo keep everyone's fixes in one place: broker URLs, legal clocks, and agent gotchas go stale. Open a pull request here. You are also free to fork and publish your own version; please keep `NOTICE` and `LICENSE`.

## License of contributions

This project is Apache-2.0. By opening a pull request you license your contribution under Apache-2.0 (inbound = outbound; Apache-2.0 section 5). New source files carry the same SPDX header as the existing ones.

No CLA. Add a Developer Certificate of Origin sign-off on each commit:

```text
Signed-off-by: Your Name <you@example.com>
```

(`git commit -s`)

You certify the contribution is yours to give, or that you have the right to submit it under Apache-2.0.

## What to change

High value:

- `references/brokers.md` — official opt-out URLs that still work, new brokers, PeopleConnect-style family mappings
- `STATUS.md` — `verified` / `untested` / `defunct` against the current form
- `references/dead-urls.md` — 404 / 410 / null-MX / parked paths agents must skip
- `references/jurisdictions.md` — clocks and portals, with a link to the official page
- `SKILL.md` — agent steps that failed in production (mailbox rejects, Turnstile, quoted-printable tokens, no-Python hosts)
- `references/search.md` — query packs and engine quirks
- `templates/paper-log.md` — fallback log when `ryd.py` cannot run
- `scripts/schema.sql` — only if the log cannot record a real event

Keep PII out of the repo. No sample `takedown.db`, no real listing URLs that identify a person, no DROP IDs.

## PR hygiene

- One concern per PR (a broker family, a jurisdiction, a schema change).
- Quote the official source for legal clocks.
- User-visible change: add a bullet under `## Unreleased` in `CHANGELOG.md`.
- Do not add affiliate links or paid-removal upsells.
- Match the existing tone: operations playbook, not a blog post.
- `master` requires a PR. Merges wait for GitHub Actions: `browser-smoke`, `test (3.10)`, `test (3.11)`, `test (3.12)`, `test (3.13)`. Do not merge with missing, failing, or stale checks.

Repository admins have an emergency ruleset bypass. Use it only when CI is broken or a production incident needs a hotfix. Note the reason on the PR or in the issue. Do not use it to skip review of playbook or schema changes.

## Security / abuse

This skill files **the person's own** opt-outs. Do not add anything that helps impersonate someone else, bypass a site's auth, or harvest third-party profiles.

If you found a vulnerability in the skill itself, open a private advisory if the GitHub repo has that enabled; otherwise an issue without exploit detail.
