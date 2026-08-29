# Search process

Use this after intake. Goal: find **this person's** indexed listings, not everyone with the same name.

## Tool detection

1. List search and browser tools already on the host. Do not install new ones unless the user asked.
2. Browser beats curl for people-search pages.
3. Prefer the host's native browser (OMP Chromium MCP, chrome-devtools, Pi/Hermes/OpenClaw browser, Codex/Claude computer-use) when it exists — same idea as driving Playwright/Puppeteer: real page, real form, screenshot as evidence.
4. Search APIs are for discovery. Filing still happens in a browser.

## Engine catalog

Use several. Stop when you have the ranking public listings plus the broker queue in `brokers.md`.

### Keyless (no API key)

- DuckDuckGo HTML
- Brave Search (web UI)
- Bing (web UI)
- Startpage
- Mojeek
- Qwant
- SearXNG (self-hosted preferred; public instances are shared logs)
- Google web UI in an **isolated** profile
- Site search: `site:spokeo.com "Name" City`

Jina Reader (`https://r.jina.ai/{url}`) can turn a listing URL into text for the evidence log when a browser snapshot is not needed.

### Agent / API search (if the user already has access)

- Exa — semantic ("people-search profile for Full Name in City")
- Firecrawl — search, then scrape the listing to markdown
- Brave Search API
- Tavily
- Parallel, Linkup, Perplexity
- Serper / SerpAPI / SearchAPI — Google-like SERPs

For `anonymity_mode=max`, do not send the name to a third-party search API unless they said yes. Use keyless + isolated browser.

### OpenClaw / Hermes

Those hosts often expose Brave, DuckDuckGo, SearXNG, Exa, Perplexity as native search providers. Use whatever is already configured. Do not add a paid provider as a surprise.

## Query pack

Run for legal name and each alias:

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
```

Follow hits that show this person **plus** a matching phone, street, or city. Same name in another country/state with no other overlap: skip.

## Match → log → file

1. Insert `listing` with URL, `found_via` (engine + query), and `pii_shown`.
2. Snapshot evidence.
3. File only after the row exists.

Reverse-phone teasers that hide the name behind a paywall: leftover, unless an official removal form accepts that URL.
