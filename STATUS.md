# Broker status

Per broker family, not per brand. PeopleConnect is one suppression. Status is about the **current official opt-out**, not a confirm-page screenshot.

| Status | Meaning |
| --- | --- |
| `verified` | Live opt-out confirmed against the current form (HTTP 200 on the official path, or a completed filing in field notes). |
| `untested` | URL/notes exist; form may have drifted, or this host only answered 403/Turnstile from a datacenter. Confirm in a real browser before filing. |
| `defunct` | Dead, moved, parked, null-MX, or identity-gated so the old single-form POST will fail. Skip. Use the replacement if one is listed. |

Load this file with `references/brokers.md` and `references/dead-urls.md`. Dead paths are skipped without looping. Send URL/status fixes as PRs; no PII.

Checked from this repo's network on **2026-09-01**. Datacenter 403 is **not** defunct.

## File first (indexed people-search)

| Broker / family | Status | Opt-out | Notes |
| --- | --- | --- | --- |
| Whitepages | untested | https://www.whitepages.com/suppression-requests | 403 from datacenter. Phone-verify. Property Intel is a separate product (`privacyrequest@whitepages.com`). |
| Spokeo | verified | https://www.spokeo.com/optout | 200 on `/optout`. Consumer inbox. Empty verify landing → `privacy@spokeo.com`. |
| BeenVerified | untested | https://www.beenverified.com/app/optout/search | 403 from datacenter. Email verify. |
| TruePeopleSearch | untested | https://www.truepeoplesearch.com/removal | 403 from datacenter. `.com` and `.net` are different hosts. |
| FastPeopleSearch | untested | https://www.fastpeoplesearch.com/removal | Same operator family as TruePeopleSearch. 403 from datacenter. |
| Radaris | untested | https://radaris.com/control/privacy | 403 from datacenter. Recheck name-index and regional mirrors. City-only teaser is not enough to refile. |
| Open Data USA | defunct | — | Origin parked (SOA `lander.d.parity.domains`); TLS EOF; `optout@` has **no MX**. Cancel the letter. Leftover SERP waits until other live listings are down. |
| PeopleFinders | untested | https://www.peoplefinders.com/opt-out | 403 / Turnstile common. `privacy@` has bounced. |
| USPhoneBook | untested | https://www.usphonebook.com/opt-out | 403 from datacenter. |
| MyLife | untested | https://www.mylife.com/privacyrequest | 403 from datacenter. Jotforms can 410; a 410 can still SERP. |
| Nuwber | untested | https://nuwber.com/optout | 403 from datacenter. |
| ThatsThem | untested | https://thatsthem.com/optout | 403 from datacenter. |
| Sync.me | untested | site privacy / opt-out | Reverse-phone app. Confirm live URL before filing. |
| ClustrMaps | untested | site privacy / opt-out | Address / map pages. |
| FamilyTreeNow | untested | site privacy / opt-out | Confirm live URL before filing. |
| Addresses.com / AnyWho / 411 | untested | site privacy / opt-out | Directory leftovers. |
| ContactOut | verified | https://contactout.com/optout | 200. Email-verify + Turnstile; one attempt. Fallback `support@contactout.com`. |
| PublicDataUSA | defunct | — | Distinct from Open Data USA. No DNS A record for `publicdatausa.com` / `www` on 2026-09-01. |
| PeekYou | untested | https://peekyou.com/about/contact/ccpa_optout/do_not_sell/ | Host `peekyou.com` resolves; `www.peekyou.com` has no A. 403 from datacenter. Fallback `ccpa@peekyou.com`. |
| PeopleSmart | untested | https://www.peoplesmart.com/optout | 403 from datacenter. Fallback `privacy@peoplesmart.com`. |
| SmartBackgroundChecks | verified | https://www.smartbackgroundchecks.com/optout | 200. Title: Record Removal Requests. Email verify. |
| SearchPeopleFree | untested | https://www.searchpeoplefree.com/opt-out | 403 from datacenter. |
| PeopleSearchNow | untested | https://www.peoplesearchnow.com/opt-out | 403 from datacenter. |
| InfoTracer | verified | https://infotracer.com/optout/ | 200. Email verify; often 24–48h. |
| SocialCatfish | verified | https://socialcatfish.com/opt-out/ | 200 → `?id=request_optout`. Fallback `ccparequest@socialcatfish.com`. |
| CheckPeople | untested | https://www.checkpeople.com/do-not-sell-info | 403 from datacenter. Written `support@` confirm can precede ~48h public lag. Do not refile. |
| National Public Data | untested | https://nationalpublicdata.com/optout.html | 403 / Turnstile from datacenter. Field notes still see unique `/people/…` URLs. One try; fallback `support@nationalpublicdata.com`. Not a SERP-first host. |

## One form, several brands

| Family | Status | Opt-out | Covers |
| --- | --- | --- | --- |
| PeopleConnect | verified | https://suppression.peopleconnect.us/ | Intelius, TruthFinder, Instant Checkmate, US Search. **One** suppression. Do not list those four as first-pass forms. |

## Upstream (may not rank)

| Broker | Status | Opt-out | Notes |
| --- | --- | --- | --- |
| Acxiom | untested | https://www.acxiom.com/optout/ | 200, but identity-gated — not a single-form POST. |
| LexisNexis people search | verified | https://optout.lexisnexis.com/ | 200. Not a credit freeze. |
| Clearbit | defunct | — | Old `/opt-out` is 404. Replacement: HubSpot. |
| HubSpot (Clearbit commercial dataset) | verified | https://www.hubspot.com/hubspot-privacy-preferences | 200. “Delete your data from HubSpot’s commercial dataset.” |
| ZoomInfo | untested | https://privacy.zoominfo.com/ | 200. Email-verify; not a bare POST. |

## Registries

Not a substitute for public people-search pages. DROP still covers registered CA brokers for CA residents. Do **not** POST a generic form to every registry row.

| Registry | Status | URL |
| --- | --- | --- |
| California DROP + broker registry | verified (portal) | https://privacy.ca.gov/drop/ and https://cppa.ca.gov/data_broker_registry/ |
| Oregon / Vermont / Texas broker registration | untested | Lookup + individual requests. Pull a bulk file only when one exists. |
