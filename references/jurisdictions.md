# Jurisdiction clocks

Confirm on the official page before telling the person a deadline. Laws change.

This is not legal advice.

## California

- Resident → **DROP first**: https://privacy.ca.gov/drop/
- Consumer app: https://consumer.drop.privacy.ca.gov/
- Status: https://consumer.drop.privacy.ca.gov/dropstatus
- Registry: https://cppa.ca.gov/data_broker_registry/
- How it works: https://privacy.ca.gov/drop/how-drop-works/
- DROP processing: brokers access DROP at least every **45 days** (began 1 Aug 2026). Status may take **90 days**.
- CCPA/CPRA deletion outside DROP: typically **45 days**, one 45-day extension with notice.
- DROP is not a substitute for public people-search opt-outs.
- One person per DROP request. Identity Gateway or existing Login.gov. Cannot switch methods after choosing.

## Other US

Use the law packs (`laws/packs/`, `ryd.py law-plan` / `law-request` / `law-event`). Each pack cites the statute text it was checked against, with the date and a hash. Packs were checked 2026-10-29 and go stale on their `review_by` date (2027-04-29); a stale pack falls back to the universal voluntary request.

| State | Response (+ extension) | Appeal answer | Authorized agent | Deletion scope | In effect |
| --- | --- | --- | --- | --- | --- |
| California | 45 (+45); ack 10 business days; opt-out 15 business days | none general | all rights | collected from the consumer | 2020-01-01 |
| Colorado | 45 (+45) | 45 (+60) | opt-out | all | 2023-07-01 |
| Connecticut | 45 (+45) | 60 | opt-out | all | 2023-07-01 |
| Delaware | 45 (+45) | 60 | opt-out | all | 2025-01-01 |
| Florida (narrow) | 45 (+15) | 60 | none found | all | 2024-07-01 |
| Indiana | 45 (+45) | 60 | none found | all | 2026-01-01 |
| Iowa | 90 (+45) | 60 | none found | provided by the consumer | 2025-01-01 |
| Kentucky | 45 (+45) | 60 | none found | all | 2026-01-01 |
| Maryland | 45 (+45) | 60 | opt-out | all | 2025-10-01 |
| Minnesota | 45 (+45) | 45 (+60) | opt-out | all | 2025-07-31 |
| Montana | 45 (+45) | 60 | opt-out | all | 2024-10-01 |
| Nebraska | 45 (+45) | 60 | opt-out | all | 2025-01-01 |
| New Hampshire | 45 (+45) | 60 | opt-out | all | 2025-01-01 |
| New Jersey | 45 (+45) | 45 | opt-out | all | 2025-01-15 |
| Oregon | 45 (+45) | 45 | opt-out | all (minimal record for third-party data) | 2024-07-01 |
| Rhode Island | 45 (+45) | 60 | opt-out | all | 2026-01-01 |
| Tennessee | 45 (+45) | 60 | none found | all | 2025-07-01 |
| Texas | 45 (+45) | 60 | opt-out | all | 2024-07-01 |
| Utah | 45 (+45) | no appeal | unverified | provided by the consumer | 2023-12-31 |
| Virginia | 45 (+45) | 60 | unverified | all | 2023-01-01 |

Days are calendar days from the controller's receipt unless marked business. Enacted but not yet in effect (no pack yet; residents get the universal request): Oklahoma and Louisiana (2027-01-01), Alabama (2027-05-01), Vermont (2028-01-01). Every other state and DC: universal voluntary request, no legal deadline.

Safeguards:

- Wording is "To the extent your organization is subject to …". A pack never says the controller is covered; thresholds and exemptions are not checked.
- Florida applies to very few companies; universal wording unless the user asserts coverage (`--controller-covered`).
- Iowa and Utah deletion covers data the consumer provided; the letter asks voluntarily for the rest.
- The consumer's appeal filing window is "reasonable", never a number.
- The Authorized agent column applies only when an agent files. A household helper filing the person's own request in their name from their own inbox (household inbox, with recorded consent or as guardian of a minor) is not agent filing; see `SKILL.md` §1.
- A clock is legal only with residency attestation, receipt date, pack version and recorded assumptions. Otherwise there is no statutory deadline in the ledger.

States with data-broker **registration** (not a California-style one-shot DROP): Texas, Oregon, Vermont. Use the registry to find brokers, then file per broker.

Google Search **Results about you** hides an address/phone **snippet**; it does not delete the broker page. Last failsafe after opt-outs: SKILL.md §7a and `references/search.md`.

## EU / EEA

- GDPR Article 17 erasure: https://gdpr-info.eu/art-17-gdpr/
- Controller must answer without undue delay, max **1 month**, extendable to **3 months** with a timely reason.
- Send `templates/erasure-request.md` to the privacy contact. Keep message-id and the public listing URL.
- If ignored: the national DPA.

## UK

- UK GDPR right to erasure. Same **1 month** pattern as GDPR. ICO guidance: https://ico.org.uk/

## Canada

- PIPEDA access/deletion to each institution. About **30 days**. Federal: OPC. Provinces may add rules (QC Law 25 is stricter).

## Australia

- Australian Privacy Principles — access / correction. About **30 days**. OAIC.

## Everywhere

If no statute is on point: still use the official free opt-out. If none, send the erasure template and start a **30-day** `legal_response` clock as a working default, labeled as policy not statute.
