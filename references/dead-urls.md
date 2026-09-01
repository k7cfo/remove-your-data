# Dead URLs

Hosts, paths, and mailboxes that 404, 410, null-MX, park, or permanently redirect off an opt-out. **Skip without looping.** File only via the replacement, if any.

`scripts/ryd.py pack` prints these as comments. Confirm a revival in a browser (not curl timeout alone) before removing a row. No PII.

| URL, host, or mailbox | How confirmed | Date (UTC) | Replacement |
| --- | --- | --- | --- |
| `optout@opendatausa.com` | DoH MX lookup: no MX. SOA `ns1.lander.d.parity.domains` (parking lander). | 2026-09-01 | `/contact` is also parked; cancel the letter. Leftover SERP is last-step after other live listings. |
| `opendatausa.com` (origin) | Parked (parity.domains lander). TLS EOF on `/`, `/contact`, `/privacy`. People and privacy URLs 404/park. | 2026-09-01 | None. Do not send a letter to a WHOIS privacy proxy after the origin parks. |
| `publicdatausa.com` / `www.publicdatausa.com` | DoH A lookup: no records. Distinct from Open Data USA. | 2026-09-01 | None until DNS returns. |
| `https://clearbit.com/opt-out` | HTTP 404 | 2026-09-01 | https://www.hubspot.com/hubspot-privacy-preferences |
| `https://www.clearbit.com/opt-out` | HTTP 404 | 2026-09-01 | https://www.hubspot.com/hubspot-privacy-preferences |
| `https://www.hubspot.com/data-privacy/request` | HTTP 404 | 2026-09-01 | https://www.hubspot.com/hubspot-privacy-preferences |
| MyLife privacy Jotform paths that return **410** | Field notes: Jotforms disappear. A 410 can still SERP; dropped pages can reappear in Bing/Yahoo. | 2026-08 | Recheck the live URL. Do not send ID alone. Do not loop the 410 path. |
| Radaris regional mirrors that **404** after the name-index drops | Field notes. Name-index URL and a regional mirror can diverge. | 2026-08 | Recheck the remaining live URL. Do not loop 404 mirrors. A city teaser with no street or phone is not enough to refile. |

National Public Data is **not** on this list: `/optout.html` is Turnstile/403 from datacenter, but unique `/people/…` URLs still appear in field notes. See `STATUS.md` (`untested`).
