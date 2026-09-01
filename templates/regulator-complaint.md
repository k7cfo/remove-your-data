# Regulator / attorney complaint

Use when a leftover is still live **after** the legal clock you logged (CCPA/CPRA deletion typically 45 days, GDPR / UK GDPR 1 month, or the statute in `references/jurisdictions.md`). Fits the ladder: official form → letter (`templates/erasure-request.md`) → regulator or attorney.

**Do not auto-send.** The person sends this, or their attorney does. Attach `exports/evidence-log.csv` and the leftover screenshots from the workspace. This is not legal advice.

Subject: Failure to delete personal information — [broker] — [listing URL]

```text
To: [state AG consumer-privacy unit / DPA / attorney]

I requested deletion of my personal information from [broker]. The public
listing is still live after the response window.

Name as listed: [exactly as shown]
Listing URL: [url]
City / region as listed: [city, region]
Other matching detail already on the listing: [phone last 4 / street — only if shown]

Requests already made (dates UTC + local, from the legal log):

1. Official opt-out / form: [date, request id, mailbox used]
2. Verify completed: [date, or "broker never sent a link"]
3. Written erasure letter: [date, destination, message-id]
4. Recheck of the exact URL: [date, what is still shown]

Legal basis (keep the lines that apply, delete the rest):
- California resident: CCPA/CPRA deletion and, if they are a data broker,
  the Delete Act / DROP. Typical deletion clock 45 days (+45 with notice).
- Other US: the consumer privacy law of [state], typically 45 days.
- EU/EEA: GDPR Article 17. One month, extendable to three with notice.
- UK: UK GDPR right to erasure. Same one-month pattern.
- Elsewhere: their published privacy policy and any applicable local law.

I am the person this record is about. I am not asking you to impersonate
anyone or to hide journalism, government, or school records.

Please require deletion of the public listing and of the underlying record
they sell, share, or license, and confirm in writing.

Regards,
[name as listed]
```

Log the send time (UTC + local), destination, and message-id. Do not paste DROP IDs, mailbox contents, or listing slugs into this git repo.
