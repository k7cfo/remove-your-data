# Search process

Use this after intake. Goal: find **this person's** indexed listings, not everyone with the same name.

One index is not enough. People-search mirrors diverge. Run the query pack on **several** providers below, then file opt-outs, then the Google failsafe.

## Tool detection

1. List search and browser tools already on the host. Do not install new ones unless the user asked.
2. Browser beats curl for people-search pages.
3. Prefer the host's native browser (OMP Chromium MCP, chrome-devtools, Pi/Hermes/OpenClaw browser, Codex/Claude computer-use) when it exists.
4. Search APIs are for discovery. Filing still happens in a browser.

## Engine catalog

Use what exists. Skip the rest. Stop when you have ranking public listings plus the broker queue in `brokers.md`.

### Host-native (use first if already wired)

Whatever this agent already searches with: OpenClaw/Hermes `web_search`, OMP/Pi web search, Claude/Codex/Cursor/Grok built-in search, Gemini grounding, Perplexity-as-tool.

OpenClaw/Hermes often expose: Brave, DuckDuckGo, SearXNG, Exa, Perplexity, Firecrawl, Tavily. Use the configured ones. Do not add a paid provider as a surprise.

### Keyless / browser (no API key)

Drive these in an **isolated** profile. Order if one is captcha-walled: next in list.

| Provider | How | Notes |
| --- | --- | --- |
| DuckDuckGo | HTML / lite UI | Default first keyless hop |
| Brave Search | web UI | Independent index |
| Bing | web UI | Feeds Yahoo, Ecosia, DuckDuckGo in part |
| Google | web UI, isolated profile | Needed later for Results about you; do not use their daily Google account for discovery if anonymity is dedicated/max |
| Startpage | web UI | Google results without a Google session |
| Yahoo | web UI | Bing-backed |
| Yandex | web UI | Often still ranks US people-search |
| Mojeek | web UI | Own crawler |
| Qwant | web UI | EU |
| SearXNG | self-host preferred | Public instances log queries — avoid for `max` |
| Ecosia | web UI | Bing-backed |
| Swisscows | web UI | |
| You.com | web UI | |
| Kagi | web UI | Only if they already have an account |
| Jina Reader | `https://r.jina.ai/{url}` | URL → markdown for evidence, not discovery |

Site search on every broker in `brokers.md`: `"Name" site:spokeo.com` etc.

### Agent / API search (only if already configured)

Do not sign the user up for a new paid search API.

| Provider | Strength |
| --- | --- |
| **Exa** | Semantic: "people-search profile for Full Name in City" |
| **Firecrawl** | Search, then scrape the listing to markdown |
| Brave Search API | Independent SERP |
| Tavily | Agent-oriented web search |
| Parallel, Linkup | Agent search |
| Perplexity API | If already on the host |
| Serper, SerpAPI, SearchAPI, ScrapingDog, SerpWow | Google-like SERPs |
| Bing Web Search API / Azure | If they already have an Azure key |
| Kagi API | If they already have Kagi |
| Jina Search | `s.jina.ai` if available |

For `anonymity_mode=max`, do not send the name to a third-party search API unless they said yes. Keyless + isolated browser only.

## Query pack

Run for legal name and each alias (`ryd.py pack` emits this from the roster):

```text
"Full Name" "City"
"Full Name" "Region"
"Full Name" "Street"
"Full Name" "Postal"
phone-with-dashes
phonedigitsonly
"Full Name" site:spokeo.com
"Full Name" site:whitepages.com
"Full Name" site:radaris.com
"Full Name" site:truepeoplesearch.com
"Full Name" site:fastpeoplesearch.com
"Full Name" site:beenverified.com
"Full Name" site:opendatausa.com
"Full Name" site:peoplefinders.com
"Full Name" site:nuwber.com
"Full Name" site:thatsthem.com
"Full Name" site:usphonebook.com
"Full Name" site:mylife.com
"Full Name" site:intelius.com
"Full Name" site:clustrmaps.com
"Full Name" site:peekyou.com
"Full Name" site:peoplesmart.com
"Full Name" site:smartbackgroundchecks.com
"Full Name" site:searchpeoplefree.com
"Full Name" site:peoplesearchnow.com
"Full Name" site:infotracer.com
"Full Name" site:socialcatfish.com
"Full Name" site:contactout.com
"Full Name" site:checkpeople.com
```

Follow hits that show this person **plus** a matching phone, street, or city. Same name in another country/state with no other overlap: skip. Skip `keep_host` / `keep_url` on the roster. Default skip: articles, LinkedIn, non-broker coverage.

## Match → log → file

1. Insert `listing` with URL, `found_via` (engine + query), and `pii_shown`.
2. Snapshot evidence.
3. File the **broker opt-out** first (SKILL.md §7 file pass).
4. Recheck the public URL (verify pass). Confirm page is not success.
5. If it still ranks on Google (or Bing) **and the source URL is down**, run the **index failsafe** below.

Reverse-phone teasers that hide the name behind a paywall: leftover, unless an official removal form accepts that URL.

## New-host watch

On each search pass, collect people-search / data-broker **hostnames** from hits that match this person. Diff against `$WORKSPACE/exports/serp-hosts.txt` (create on first pass). Alert when name+city/phone/street shows up on a **new** host. Append the new hosts. Do not file SERP hides against allowlisted hosts. Engine removal stays last-step.

## Index failsafe — Google Results about you

This does **not** delete the broker page. It asks Google to **stop showing** a result (or stop showing it for name queries). Source can stay live. That is why it is last, after the free opt-out, and **only after the source listing is 404/410/gone**. Stale snippets after a parked origin are expected.

Official:

- Results about you: [https://myactivity.google.com/results-about-you](https://myactivity.google.com/results-about-you)
- How-to: [https://support.google.com/websearch/answer/12719076](https://support.google.com/websearch/answer/12719076)
- Broader private-info form: [https://support.google.com/websearch/answer/9673730](https://support.google.com/websearch/answer/9673730)
- Detailed form (no login, someone else, paywall, or Results-about-you denied): [https://support.google.com/websearch/contact/content_removal_form](https://support.google.com/websearch/contact/content_removal_form)

### SERP click (what they meant by “next to the listing”)

On **desktop or mobile Google Search**, signed into **their** account (not yours):

1. Search the name + city (or the leftover URL).
2. On the result: **More** (⋮) → **About this result** → **Remove result** → **It shows my personal info and I don't want it there** → **Contact Info**.
3. Enter the name and the contact info **exactly as shown** on that result (nickname, old address, one phone is enough).
4. Submit. Log `action_log.action = google_serp_remove`, request ID from the confirm email, leftover URL.
5. Status lives in Results about you → Removal requests (In progress / Approved / Denied / Undone).

### Results about you (monitoring + bulk)

Same Google account. Get started → enter name, aliases, phones, addresses, emails from the **roster**. Optional notifications. Review **To review** → **Request to remove** per hit.

Do **not** run this from the agent's Google account on behalf of the person — Google may deny it. Hand them the session, or use the detailed form.

### When to use which

| Situation | Path |
| --- | --- |
| Leftover still in Google SERP after opt-out window | SERP ⋮ → Remove result |
| Want ongoing monitoring | Results about you |
| Not signed in, filing for family, paywalled page, or SERP path missing | Detailed removal form |
| Under 18 | Detailed form only |
| Government / school / newspaper URL | Often no Remove option — leftover, contact the site or letter |

Google will not usually hide pages they consider public-interest (gov, education, news). Removing from Search does not remove Bing/Yandex/the source.

### Other indexes (after Google)

- **Bing** content removal: [https://www.bing.com/webmaster/tools/content-removal](https://www.bing.com/webmaster/tools/content-removal) — covers a chunk of Yahoo/Ecosia/DDG.
- DuckDuckGo has no separate people-search removal; it mostly inherits Bing.
- Yandex: their webmaster / content-complaint flow if the leftover still ranks there.

Log each as `google_serp_remove` or `index_hide` in `action_log` with the engine in `channel` (`google`, `bing`, `yandex`).
