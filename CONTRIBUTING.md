# Contributing

Thank you for making this skill more effective. The point of a public repo is a single queue of broker URLs, legal clocks, and agent gotchas — not a dozen drifting copies.

## Canonical repository

This repository is the project. Please:

1. Open an issue or pull request **here**.
2. Use a GitHub fork only to send that pull request, then ignore the fork.
3. Do not publish a packaged / renamed / "improved" copy as its own project.

GitHub will still show a Fork button. That is a platform feature, not an invitation to split the work.

## License of contributions

This project is AGPL-3.0-or-later. By opening a pull request you license your contribution under AGPL-3.0-or-later (inbound = outbound). Keep new files under the same license.

No CLA. Add a Developer Certificate of Origin sign-off on each commit:

```text
Signed-off-by: Your Name <you@example.com>
```

(`git commit -s`)

You certify the contribution is yours to give, or that you have the right to submit it under the AGPL.

## What to change

High value:

- `references/brokers.md` — official opt-out URLs that still work, new brokers, PeopleConnect-style family mappings
- `references/jurisdictions.md` — clocks and portals, with a link to the official page
- `SKILL.md` — agent steps that failed in production (mailbox rejects, Turnstile, quoted-printable tokens)
- `references/search.md` — query packs and engine quirks
- `scripts/schema.sql` — only if the log cannot record a real event

Keep PII out of the repo. No sample `takedown.db`, no real listing URLs that identify a person, no DROP IDs.

## PR hygiene

- One concern per PR (a broker family, a jurisdiction, a schema change).
- Quote the official source for legal clocks.
- Do not add affiliate links or paid-removal upsells.
- Match the existing tone: operations playbook, not a blog post.

## Security / abuse

This skill files **the person's own** opt-outs. Do not add anything that helps impersonate someone else, bypass a site's auth, or harvest third-party profiles.

If you found a vulnerability in the skill itself, open a private advisory if the GitHub repo has that enabled; otherwise an issue without exploit detail.
