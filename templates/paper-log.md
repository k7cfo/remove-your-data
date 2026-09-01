# Paper takedown log

Use when this host cannot run `python3 scripts/ryd.py`. Copy **outside** the git clone. Never commit PII.

Same facts as SQLite: roster, actions, clocks, leftovers. CSV/markdown is the system of record until they have Python — then `ryd.py init` and copy these rows in.

```text
$WORKSPACE/
  roster.md          # this file, or split tables
  action-log.csv
  leftovers.md
  clocks.md
  serp-hosts.txt
  evidence/YYYY-MM-DD/
```

chmod 700 the folder if you can.

## Roster

| field | person 1 | person 2 |
| --- | --- | --- |
| legal_name | | |
| relationship | self | |
| consent_basis | self | |
| residency_country | | |
| residency_region | | |
| city | | |
| cadence_hours | 168 | |
| anonymity_mode | dedicated | |
| verify_email | | |
| keep_host / keep_url | | |
| intake_complete | 0 | |
| drop_filed | 0 | |

Identifiers (one row each): kind (`alias`, `address`, `phone`, `keep_host`, …), value, scan 0/1.

## action-log.csv

```text
occurred_at_utc,occurred_at_local,actor,person,broker,listing_url,action,channel,request_id,result,evidence_path
```

One row per real action. Actor: `agent`, `user`, `family`.

## Clocks

| person | kind | legal_basis | due_at_utc | status | listing_url | notes |
| --- | --- | --- | --- | --- | --- | --- |

Kinds: `verify_email`, `site_window`, `legal_response`, `drop_45d`, `drop_90d`, `rescan`, `relist_90d`.

## Leftovers

| broker | url | pii_shown | why | next_step | open |
| --- | --- | --- | --- | --- | --- |

## Coach line (no files)

If the agent cannot write a folder, speak one log line after each action and tell them to paste it into their notes. Next session they paste the notes back first.

```text
utc=… local=… person=… broker=… url=… action=… channel=… request_id=… result=…
```
