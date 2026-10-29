# Broker queue

Starting queue for public people-search and related opt-outs. URLs rot. Before filing: open the live privacy / opt-out page; load [`STATUS.md`](../STATUS.md) and [`dead-urls.md`](dead-urls.md). Skip dead rows without looping. Status is `verified` / `untested` / `defunct`. If a URL is dead, file anyway via the site's current privacy page only when STATUS is not `defunct`, then send a PR that fixes this file.

Family members: file each opt-out from that person's own inbox when the helper has permission to use it (household inbox, `SKILL.md` §1) so verify links and OTP codes land there; record consent with `ryd.py record-filer` first.

Do not pay a site to remove a listing. Registry membership is not a spray list — `python3 scripts/registry_pull.py` diffs hostnames; do not POST a generic form to every row.

## File first (indexed people-search)

| Broker | Opt-out | Notes |
| --- | --- | --- |
| Whitepages | https://www.whitepages.com/suppression-requests | Often verifies with an automated phone call. Extra profiles per old address. Property Intel: email privacyrequest@. Auto-replies may omit California; reply on the same thread (CCPA/CPRA/Delete Act). A same-thread follow-up can mint a new Zendesk number; treat as the same request, do not reply again. |
| Spokeo | https://www.spokeo.com/optout | Paste profile URL. Keep request id. Consumer inbox; some agent domains rejected. Drop window often 24–48h. |
| BeenVerified | https://www.beenverified.com/app/optout/search | Email verify. |
| TruePeopleSearch | https://www.truepeoplesearch.com/removal | Datacenter IP often 403. File FastPeopleSearch too. `truepeoplesearch.net` is a different host; opt-out can be a Google Form that needs a signed-in consumer Google account. |
| FastPeopleSearch | https://www.fastpeoplesearch.com/removal | Same operator family as TruePeopleSearch. |
| FastBackgroundCheck | https://www.fastbackgroundcheck.com/opt-out | Sister of FastPeopleSearch. Datacenter curl often CF challenge; non-curl fetch can read pages. Opt-out = name+email+captcha then emailed form (~3 days). Relative pages can reprint subject phones. |
| Radaris | https://radaris.com/control/privacy | Confirm email required. Recheck name-index and regional mirrors. |
| Open Data USA | origin parked | **defunct.** No MX for `optout@`. Cancel the letter. Leftover SERP last-step. |
| PeopleFinders | https://www.peoplefinders.com/opt-out | Public form may be Turnstile-blocked; `privacy@` has bounced. Log and move. |
| USPhoneBook | https://www.usphonebook.com/opt-out | Reverse-phone. |
| MyLife | https://www.mylife.com/privacyrequest | Slow. Jotforms can disappear; do not send ID alone. A 410 can still SERP; dropped pages can reappear in Bing/Yahoo. Atlassian support can confirm account + published-profile deletion and quote 3–5 business days for a full purge; origin can go 404. Watch 24–72h. Do not file SERP while leftover origins are still live. |
| Nuwber | https://nuwber.com/optout | |
| ThatsThem | https://thatsthem.com/optout | |
| Sync.me | site privacy / opt-out | Reverse-phone app. HTTP 200 can still say Unknown or misparse a number; no matching person/identifier = false positive, not leftover. |
| CyberBackgroundChecks | https://www.cyberbackgroundchecks.com/removal | `/removal` often Turnstile from datacenter. One attempt. No subject detail/PID with matching IDs while household has one: do not invent subject filing; household only if easy. |
| ClustrMaps | site privacy / opt-out | Address / map pages. |
| FamilyTreeNow | site privacy / opt-out | |
| Addresses.com / AnyWho / 411 | site privacy / opt-out | Directory leftovers. |
| ContactOut | https://contactout.com/optout | CA-registered B2B finder. `/optout` is email-verify + Turnstile; datacenter often fails. Fallback `support@contactout.com`. Do not loop Turnstile. |
| PublicDataUSA | — | **defunct.** No DNS for `publicdatausa.com` (2026-09-01). Distinct from Open Data USA. |
| PeekYou | https://peekyou.com/about/contact/ccpa_optout/do_not_sell/ | `www.peekyou.com` has no A. 403 from datacenter. Fallback `ccpa@peekyou.com`. |
| CheckPeople | https://www.checkpeople.com/do-not-sell-info | `support@` can confirm expunge while the public URL lags or stays CF-blocked ~48h. After that, a Google name-index `/name/…` snippet can still show PII while origin is CF. Do not refile. SERP last-step. |
| National Public Data | https://nationalpublicdata.com/optout.html | Unique `/people/…` URL required. `/optout.html` is Turnstile; datacenter often fails. One try. Fallback `support@nationalpublicdata.com` with the profile URL. Vendor confirm can cover unique + name-index; watch 24–72h for reappear. Do not file SERP while leftover origins are still live. |
| PeopleSmart | https://www.peoplesmart.com/optout | 403 from datacenter. Fallback `privacy@peoplesmart.com`. |
| SmartBackgroundChecks | https://www.smartbackgroundchecks.com/optout | Email verify. Live 200 on 2026-09-01. |
| SearchPeopleFree | https://www.searchpeoplefree.com/opt-out | 403 from datacenter. |
| PeopleSearchNow | https://www.peoplesearchnow.com/opt-out | 403 from datacenter. |
| InfoTracer | https://infotracer.com/optout/ | Email verify; often 24–48h. Live 200 on 2026-09-01. |
| SocialCatfish | https://socialcatfish.com/opt-out/ | Live 200 → `?id=request_optout`. Fallback `ccparequest@socialcatfish.com`. |

## One form, several brands

| Family | Opt-out | Covers |
| --- | --- | --- |
| PeopleConnect | https://suppression.peopleconnect.us/ | Intelius, TruthFinder, Instant Checkmate, US Search. Confirmation can be name-based only; allow ~48h, then sweep every household phone and address on all siblings. Exact non-name leftovers go in the same support thread (carve out numbers/pages that are not the subject); not a fresh suppression or four separate filings. Residual auto-ack quoting a processing window ≠ done — watch; do not nag. |

## Upstream (may not rank, still feeds others)

| Broker | Opt-out | Notes |
| --- | --- | --- |
| Acxiom | https://www.acxiom.com/optout/ | Identity-gated. Not a single-form POST. |
| LexisNexis people search | https://optout.lexisnexis.com/ | Not a credit freeze. |
| Clearbit | — | Old `/opt-out` 404. Use HubSpot. |
| HubSpot (Clearbit dataset) | https://www.hubspot.com/hubspot-privacy-preferences | Delete from HubSpot’s commercial dataset. |
| ZoomInfo | https://privacy.zoominfo.com/ | Email-verify. Not a bare POST. |

## Registries (not a substitute for public pages)

| Registry | URL | Who |
| --- | --- | --- |
| California DROP + broker registry | https://privacy.ca.gov/drop/ and https://cppa.ca.gov/data_broker_registry/ | CA residents first. CSV: `scripts/registry_pull.py` (hostname diff only). |
| Oregon data broker registry | https://dfr.oregon.gov/business/licensing/data-broker-registry/pages/index.aspx | Lookup + individual requests |
| Vermont data broker registry | Vermont Secretary of State data broker inquiry | Lookup + individual requests |
| Texas data broker registration | Texas Secretary of State / AG materials | Lookup + individual requests |

## Outside the US (add via PR)

Search the local equivalent of people-search / directory / data broker, then file GDPR / UK GDPR / local statute:

- UK: 192.com, 118 118, and any people-search mirrors that rank
- EU: national directories, marketing-file opt-outs, and each controller's privacy email
- Elsewhere: whatever ranked in the search pack for their name + city

When you discover a durable official opt-out URL, add it here.
