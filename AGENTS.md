# Repo map

This repository is the **remove-your-data** skill plus a stdlib dashboard. Product behavior lives in `SKILL.md`. Do not put a takedown workspace or anyone's PII in this tree.

| Path | What |
| --- | --- |
| `SKILL.md` | Agent playbook. First run is intake. CA → DROP first. |
| `references/` | Broker queue, jurisdiction clocks, search process |
| `templates/erasure-request.md` | Letter when a site has no form |
| `scripts/schema.sql` | SQLite legal log |
| `scripts/ryd.py` | `init` / `serve` / `export` / `export-csv` |
| `LICENSE` | AGPL-3.0-or-later |
| `CONTRIBUTING.md` | PRs to this repo only; DCO; no long-lived forks |

Dashboard binds 127.0.0.1. Do not add a public host option.

Python is stdlib-only. Do not add a dependency without a documented reason in the PR.
