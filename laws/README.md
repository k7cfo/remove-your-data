# Law packs

Versioned data for US state consumer privacy laws. `scripts/ryd_laws.py` loads
them; `ryd.py law-plan` / `law-request` / `law-event` use them. Not legal advice.

| Path | What |
| --- | --- |
| `schema.json` | Pack shape (documentation). `ryd_laws.validate_pack()` enforces it. |
| `packs/us-xx.json` | One pack per state law in effect. |
| `packs/us-universal.json` | Voluntary request for any state or DC. No statute, no deadline. |
| `templates/*.txt` | Request and appeal wording (`string.Template`). |

## Rules

- Every clock names a `source` and a `cite`. Every source has a URL, `checked_on`
  date and the sha256 of the bytes fetched that day.
- Day counts are calendar days unless `day_type` is `business`. Business days
  skip weekends and US federal holidays only.
- Clocks count from the controller's **receipt** date, recorded by the user.
- Appeal filing windows are never numbers. Statutes say "reasonable period".
- `authorized_agent`: `true` (statute allows it), `false` (no provision found in
  the text checked), `null` (unverified). A request sent by an agent fails for
  `false` rights and warns for `null`.
- Selection falls back to `us-universal` when: no pack, the law is not yet in
  effect, the pack is superseded without a replacement, `review_by` has passed,
  status is not `current`, no residency attestation, or the law is `narrow`
  (Florida) and the user did not assert the controller is covered.
- Wording says "To the extent your organization is subject to ...". It never
  says a controller is covered.

## Updating a pack

1. Re-read the primary sources. Do not copy numbers from secondary summaries.
2. Bump `pack_version` (YYYY.MM.DD), `verified_on`, `review_by` (about six
   months later), each source's `checked_on` and `sha256`, and add a
   `changelog` entry.
3. If the law changed, keep the old file history in git and say what changed in
   the changelog. Requests already recorded keep their old `pack_version`; the
   ledger refuses to open new statutory clocks on them until re-planned.
4. Run `python3 scripts/ryd.py law-validate` and the tests.

A law that is enacted but not yet in effect gets no pack until its effective
date; until then residents get the universal request.
