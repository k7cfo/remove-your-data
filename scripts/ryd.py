#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Workspace helper and localhost running-report dashboard. Stdlib only."""

from __future__ import annotations

import argparse
import csv
import io
import os
import sqlite3
import stat
import sys
from datetime import datetime, timedelta, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
STATUSES = (
    "found",
    "filed",
    "pending_verify",
    "pending_drop",
    "gone",
    "leftover",
    "blocked",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    return (dt or utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def connect(db: Path, readonly: bool) -> sqlite3.Connection:
    if readonly:
        uri = db.resolve().as_uri() + "?mode=ro"
        con = sqlite3.connect(uri, uri=True)
    else:
        con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_workspace(workspace: Path) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "evidence").mkdir(exist_ok=True)
    (workspace / "exports").mkdir(exist_ok=True)
    db = workspace / "takedown.db"
    sql = SCHEMA.read_text(encoding="utf-8")
    with sqlite3.connect(db) as con:
        con.executescript(sql)
    os.chmod(workspace, stat.S_IRWXU)
    os.chmod(db, stat.S_IRUSR | stat.S_IWUSR)
    return db


def seed_demo(con: sqlite3.Connection) -> None:
    now = utcnow()
    started = utc_iso(now - timedelta(days=2))
    due_over = utc_iso(now - timedelta(hours=6))
    due_soon = utc_iso(now + timedelta(days=5))
    drop_due = utc_iso(now + timedelta(days=43))
    con.execute(
        """
        INSERT INTO person (
          legal_name, residency_country, residency_region, timezone,
          cadence_hours, anonymity_mode, household_scope, intake_complete,
          created_at_utc, notes
        ) VALUES (?, 'US', 'CA', 'America/Los_Angeles', 168, 'dedicated', 0, 1, ?, ?)
        """,
        (
            "Jane Q. Public (DEMO)",
            started,
            "Synthetic demo row. Not a real person.",
        ),
    )
    pid = con.execute("SELECT id FROM person").fetchone()[0]
    con.executemany(
        "INSERT INTO identifier (person_id, kind, value, normalized) VALUES (?, ?, ?, ?)",
        [
            (pid, "name", "Jane Q. Public", "jane q public"),
            (pid, "city", "Sacramento", "sacramento"),
        ],
    )
    con.executemany(
        "INSERT INTO broker (name, family, optout_url, channel) VALUES (?, ?, ?, ?)",
        [
            ("Spokeo", None, "https://www.spokeo.com/optout", "form"),
            ("Whitepages", None, "https://www.whitepages.com/suppression-requests", "form"),
            ("TruePeopleSearch", None, "https://www.truepeoplesearch.com/removal", "form"),
            ("PeopleConnect", "peopleconnect", "https://suppression.peopleconnect.us/", "form"),
        ],
    )
    brokers = {
        row["name"]: row["id"]
        for row in con.execute("SELECT id, name FROM broker")
    }

    def listing(broker: str, url: str, status: str, pii: str, req: str | None = None) -> int:
        con.execute(
            """
            INSERT INTO listing (
              person_id, broker_id, url, found_via, pii_shown, status,
              email_used, request_id, created_at_utc, updated_at_utc
            ) VALUES (?, ?, ?, 'demo search', ?, ?, 'demo@example.com', ?, ?, ?)
            """,
            (pid, brokers[broker], url, pii, status, req, started, utc_iso()),
        )
        return int(con.execute("SELECT last_insert_rowid()").fetchone()[0])

    spokeo = listing(
        "Spokeo",
        "https://www.spokeo.com/p/demo-not-real",
        "pending_verify",
        "name, city",
        "optout_demo_1",
    )
    wp = listing(
        "Whitepages",
        "https://www.whitepages.com/name/demo-not-real",
        "gone",
        "name, street teaser",
        "wp_demo",
    )
    tps = listing(
        "TruePeopleSearch",
        "https://www.truepeoplesearch.com/find/demo-not-real",
        "blocked",
        "name, phone last-4",
    )
    pc = listing(
        "PeopleConnect",
        "https://www.intelius.com/people-search/demo-not-real",
        "leftover",
        "name, relatives teaser",
    )
    con.execute(
        """
        INSERT INTO leftover (listing_id, why, next_step, open, updated_at_utc)
        VALUES (?, ?, ?, 1, ?)
        """,
        (
            tps,
            "403 / Turnstile from datacenter IP",
            "Retry from residential browser or letter",
            utc_iso(),
        ),
    )
    con.execute(
        """
        INSERT INTO leftover (listing_id, why, next_step, open, updated_at_utc)
        VALUES (?, ?, ?, 1, ?)
        """,
        (
            pc,
            "Suppression confirmed; public URL still teases household",
            "Recheck at site_window; escalate if still live",
            utc_iso(),
        ),
    )
    con.executemany(
        """
        INSERT INTO clock (
          person_id, listing_id, broker_id, kind, legal_basis,
          started_at_utc, due_at_utc, status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                pid,
                spokeo,
                brokers["Spokeo"],
                "verify_email",
                "site TOS",
                started,
                due_over,
                "overdue",
                "Confirm link not clicked",
            ),
            (
                pid,
                wp,
                brokers["Whitepages"],
                "site_window",
                "site window 48h",
                started,
                due_soon,
                "done",
                "Public URL 404",
            ),
            (
                pid,
                None,
                None,
                "drop_45d",
                "CA DROP 45-day cycle",
                started,
                drop_due,
                "open",
                "DROP filed (demo)",
            ),
            (
                pid,
                None,
                None,
                "rescan",
                "user cadence",
                started,
                utc_iso(now + timedelta(days=5)),
                "open",
                None,
            ),
        ],
    )
    con.executemany(
        """
        INSERT INTO action_log (
          person_id, listing_id, broker_id, actor, action, channel,
          request_id, result, evidence_path, listing_url,
          occurred_at_utc, occurred_at_local
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                pid,
                None,
                None,
                "agent",
                "intake",
                "cli",
                None,
                "complete",
                None,
                None,
                started,
                started,
            ),
            (
                pid,
                None,
                None,
                "user",
                "drop_submit",
                "browser",
                "DROP-DEMO",
                "submitted",
                None,
                "https://consumer.drop.privacy.ca.gov/",
                utc_iso(now - timedelta(days=1, hours=4)),
                utc_iso(now - timedelta(days=1, hours=4)),
            ),
            (
                pid,
                spokeo,
                brokers["Spokeo"],
                "agent",
                "file_optout",
                "form",
                "optout_demo_1",
                "pending_verify",
                None,
                "https://www.spokeo.com/p/demo-not-real",
                utc_iso(now - timedelta(hours=20)),
                utc_iso(now - timedelta(hours=20)),
            ),
            (
                pid,
                wp,
                brokers["Whitepages"],
                "user",
                "phone_verify",
                "phone",
                "wp_demo",
                "gone",
                None,
                "https://www.whitepages.com/name/demo-not-real",
                utc_iso(now - timedelta(hours=8)),
                utc_iso(now - timedelta(hours=8)),
            ),
        ],
    )
    con.execute(
        """
        INSERT INTO email_event (
          person_id, listing_id, mailbox, from_domain, subject,
          received_at_utc, had_code_or_link, handled
        ) VALUES (?, ?, ?, ?, ?, ?, 1, 0)
        """,
        (
            pid,
            spokeo,
            "demo@example.com",
            "spokeo.com",
            "Confirm your Spokeo opt-out (demo)",
            utc_iso(now - timedelta(hours=19)),
        ),
    )
    con.execute(
        "INSERT INTO config (key, value) VALUES ('drop_filed', '1')"
    )
    con.commit()


def load_report(con: sqlite3.Connection) -> dict[str, Any]:
    person = con.execute("SELECT * FROM person ORDER BY id LIMIT 1").fetchone()
    now = utcnow()
    counts = {status: 0 for status in STATUSES}
    total = 0
    if person:
        for row in con.execute(
            "SELECT status, COUNT(*) AS n FROM listing WHERE person_id = ? GROUP BY status",
            (person["id"],),
        ):
            counts[row["status"]] = row["n"]
            total += row["n"]
    clocks = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              c.id, c.kind, c.legal_basis, c.started_at_utc, c.due_at_utc,
              c.status, c.notes, b.name AS broker, l.url AS listing_url
            FROM clock c
            LEFT JOIN broker b ON b.id = c.broker_id
            LEFT JOIN listing l ON l.id = c.listing_id
            ORDER BY c.due_at_utc ASC
            """
        )
    ]
    open_clocks = []
    overdue = []
    for clock in clocks:
        due = parse_utc(clock["due_at_utc"])
        clock["overdue"] = bool(
            clock["status"] in ("open", "overdue")
            and due is not None
            and due <= now
        )
        if clock["status"] in ("open", "overdue"):
            open_clocks.append(clock)
            if clock["overdue"] or clock["status"] == "overdue":
                overdue.append(clock)
    listings = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              l.id, l.url, l.status, l.found_via, l.pii_shown, l.request_id,
              l.updated_at_utc, b.name AS broker
            FROM listing l
            LEFT JOIN broker b ON b.id = l.broker_id
            ORDER BY
              CASE l.status
                WHEN 'blocked' THEN 0
                WHEN 'leftover' THEN 1
                WHEN 'pending_verify' THEN 2
                WHEN 'pending_drop' THEN 3
                WHEN 'found' THEN 4
                WHEN 'filed' THEN 5
                ELSE 6
              END,
              l.updated_at_utc DESC
            """
        )
    ]
    leftovers = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              lo.id, lo.why, lo.next_step, lo.updated_at_utc,
              l.url, l.status, b.name AS broker
            FROM leftover lo
            JOIN listing l ON l.id = lo.listing_id
            LEFT JOIN broker b ON b.id = l.broker_id
            WHERE lo.open = 1
            ORDER BY lo.updated_at_utc DESC
            """
        )
    ]
    emails = [
        dict(row)
        for row in con.execute(
            """
            SELECT mailbox, from_domain, subject, received_at_utc,
                   had_code_or_link, handled, l.url AS listing_url
            FROM email_event e
            LEFT JOIN listing l ON l.id = e.listing_id
            ORDER BY received_at_utc DESC
            LIMIT 50
            """
        )
    ]
    log = [
        dict(row)
        for row in con.execute(
            """
            SELECT occurred_at_utc, occurred_at_local, actor, person,
                   broker, listing_url, action, channel, request_id,
                   result, evidence_path
            FROM v_evidence_chronology
            ORDER BY occurred_at_utc DESC
            LIMIT 200
            """
        )
    ]
    drop_filed = con.execute(
        "SELECT value FROM config WHERE key = 'drop_filed'"
    ).fetchone()
    next_due = None
    for clock in open_clocks:
        due = parse_utc(clock["due_at_utc"])
        if due and (next_due is None or due < next_due):
            next_due = due
    return {
        "generated_at": utc_iso(now),
        "person": dict(person) if person else None,
        "counts": counts,
        "total": total,
        "open_clocks": open_clocks,
        "overdue": overdue,
        "listings": listings,
        "leftovers": leftovers,
        "emails": emails,
        "log": log,
        "drop_filed": bool(drop_filed and drop_filed["value"] not in ("0", "")),
        "next_due": utc_iso(next_due) if next_due else None,
        "unhandled_mail": sum(1 for row in emails if not row["handled"]),
    }


def cadence_label(hours: int | None) -> str:
    if not hours:
        return "—"
    if hours % 24 == 0:
        days = hours // 24
        return f"every {days}d"
    return f"every {hours}h"


def pill(status: str) -> str:
    return f'<span class="pill {escape(status)}">{escape(status.replace("_", " "))}</span>'


def cell(value: Any, url: bool = False) -> str:
    if value is None or value == "":
        return "<td class='empty'>—</td>"
    text = str(value)
    if url and text.startswith("http"):
        return (
            f'<td><a href="{escape(text, quote=True)}" rel="noreferrer">'
            f"{escape(text)}</a></td>"
        )
    return f"<td>{escape(text)}</td>"


def table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return '<p class="muted">None.</p>'
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(cols) + "</tr>" for cols in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_html(report: dict[str, Any], *, live: bool) -> str:
    person = report["person"]
    title = "Takedown report"
    banner = ""
    if person:
        title = f"{person['legal_name']} — takedown report"
        if "DEMO" in person["legal_name"]:
            banner = (
                '<div class="banner demo">Demo data. Not a real person. '
                "Bind this dashboard to your workspace when you have one.</div>"
            )
    elif live:
        banner = (
            '<div class="banner warn">No person in this database yet. '
            "Run intake, then refresh.</div>"
        )
    else:
        banner = '<div class="banner warn">Empty workspace.</div>'

    residency = "—"
    meta = []
    if person:
        residency = ", ".join(
            part
            for part in (person.get("residency_region"), person.get("residency_country"))
            if part
        )
        meta = [
            ("Residency", residency),
            ("Anonymity", person.get("anonymity_mode")),
            ("Cadence", cadence_label(person.get("cadence_hours"))),
            ("Timezone", person.get("timezone")),
            ("DROP", "filed" if report["drop_filed"] else "not filed"),
            ("Next clock", report["next_due"] or "—"),
        ]

    counts = report["counts"]
    cards = [
        ("Listings", str(report["total"])),
        ("Gone", str(counts["gone"])),
        ("Pending", str(counts["pending_verify"] + counts["pending_drop"] + counts["filed"] + counts["found"])),
        ("Leftover", str(counts["leftover"])),
        ("Blocked", str(counts["blocked"])),
        ("Overdue clocks", str(len(report["overdue"]))),
        ("Open mail", str(report["unhandled_mail"])),
    ]
    card_html = "".join(
        f'<div class="card"><div class="n">{escape(n)}</div>'
        f'<div class="k">{escape(k)}</div></div>'
        for k, n in cards
    )
    meta_html = "".join(
        f"<div><dt>{escape(k)}</dt><dd>{escape(str(v or '—'))}</dd></div>"
        for k, v in meta
    )

    overdue_rows = [
        [
            cell(c["due_at_utc"]),
            cell(c["kind"]),
            cell(c["broker"]),
            cell(c["legal_basis"]),
            cell(c["listing_url"], url=True),
            cell(c["notes"]),
        ]
        for c in report["overdue"]
    ]
    clock_rows = [
        [
            cell(c["due_at_utc"]),
            f"<td>{pill('overdue' if c['overdue'] else c['status'])}</td>",
            cell(c["kind"]),
            cell(c["broker"]),
            cell(c["legal_basis"]),
            cell(c["listing_url"], url=True),
            cell(c["notes"]),
        ]
        for c in report["open_clocks"]
    ]
    listing_rows = [
        [
            cell(row["broker"]),
            f"<td>{pill(row['status'])}</td>",
            cell(row["url"], url=True),
            cell(row["pii_shown"]),
            cell(row["request_id"]),
            cell(row["updated_at_utc"]),
        ]
        for row in report["listings"]
    ]
    leftover_rows = [
        [
            cell(row["broker"]),
            cell(row["url"], url=True),
            cell(row["why"]),
            cell(row["next_step"]),
            cell(row["updated_at_utc"]),
        ]
        for row in report["leftovers"]
    ]
    mail_rows = [
        [
            cell(row["received_at_utc"]),
            f"<td>{pill('open' if not row['handled'] else 'done')}</td>",
            cell(row["from_domain"]),
            cell(row["subject"]),
            cell(row["mailbox"]),
            cell(row["listing_url"], url=True),
        ]
        for row in report["emails"]
    ]
    log_rows = [
        [
            cell(row["occurred_at_utc"]),
            cell(row["actor"]),
            cell(row["broker"]),
            cell(row["action"]),
            cell(row["channel"]),
            cell(row["request_id"]),
            cell(row["result"]),
            cell(row["listing_url"], url=True),
        ]
        for row in report["log"]
    ]

    refresh = (
        '<meta http-equiv="refresh" content="30">'
        if live
        else ""
    )
    live_note = (
        '<p class="muted">Localhost only. Refreshes every 30s. '
        '<a href="/export.csv">CSV chronology</a> · '
        '<a href="/report.html">Snapshot HTML</a></p>'
        if live
        else '<p class="muted">Static snapshot. Not served live.</p>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}
<title>{escape(title)}</title>
<style>
:root {{
  --bg: #0e1116;
  --fg: #e6edf3;
  --muted: #8b949e;
  --card: #161b22;
  --line: #30363d;
  --accent: #58a6ff;
  --gone: #3fb950;
  --warn: #d29922;
  --bad: #f85149;
  --pending: #a371f7;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--fg);
  font: 14px/1.45 ui-sans-serif, system-ui, sans-serif;
}}
header, main {{ max-width: 1200px; margin: 0 auto; padding: 1.25rem 1.5rem; }}
h1 {{ font-size: 1.35rem; font-weight: 650; margin: 0 0 .35rem; }}
h2 {{ font-size: 1rem; margin: 1.75rem 0 .6rem; font-weight: 650; }}
.muted {{ color: var(--muted); }}
.banner {{
  padding: .7rem 1rem; border-radius: 8px; margin: .8rem 0 1rem;
  border: 1px solid var(--line); background: var(--card);
}}
.banner.demo {{ border-color: var(--warn); }}
.banner.warn {{ border-color: var(--bad); }}
.dl {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: .6rem 1rem; margin: 1rem 0;
}}
.dl dt {{ color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; }}
.dl dd {{ margin: 0; font-weight: 600; }}
.cards {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: .6rem; margin: 1rem 0 1.4rem;
}}
.card {{
  background: var(--card); border: 1px solid var(--line);
  border-radius: 10px; padding: .75rem .8rem;
}}
.card .n {{ font-size: 1.45rem; font-weight: 700; }}
.card .k {{ color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; }}
table {{
  width: 100%; border-collapse: collapse; background: var(--card);
  border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
}}
th, td {{
  text-align: left; padding: .45rem .6rem; border-bottom: 1px solid var(--line);
  vertical-align: top;
}}
td:first-child {{ white-space: nowrap; }}
th {{ color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; font-weight: 600; }}
tr:last-child td {{ border-bottom: 0; }}
td.empty {{ color: var(--muted); }}
td a {{ overflow-wrap: anywhere; word-break: break-all; }}
a {{ color: var(--accent); }}
.pill {{
  display: inline-block; padding: .1rem .45rem; border-radius: 999px;
  font-size: .72rem; font-weight: 650; text-transform: uppercase;
  letter-spacing: .03em; background: #21262d;
}}
.pill.gone, .pill.done {{ color: var(--gone); }}
.pill.overdue, .pill.blocked, .pill.leftover {{ color: var(--bad); }}
.pill.pending_verify, .pill.pending_drop, .pill.filed, .pill.found {{ color: var(--pending); }}
.pill.open {{ color: var(--warn); }}
footer {{ color: var(--muted); font-size: .8rem; margin-top: 2rem; }}
</style>
</head>
<body>
<header>
  <h1>{escape(person["legal_name"] if person else "Takedown report")}</h1>
  <p class="muted">Generated {escape(report["generated_at"])} UTC · local legal log · not legal advice</p>
  {banner}
  <div class="dl">{meta_html}</div>
  <div class="cards">{card_html}</div>
  {live_note}
</header>
<main>
  <h2>Overdue clocks</h2>
  {table(["Due UTC", "Kind", "Broker", "Basis", "Listing", "Notes"], overdue_rows)}
  <h2>Open clocks</h2>
  {table(["Due UTC", "Status", "Kind", "Broker", "Basis", "Listing", "Notes"], clock_rows)}
  <h2>Listings</h2>
  {table(["Broker", "Status", "URL", "PII shown", "Request ID", "Updated UTC"], listing_rows)}
  <h2>Leftovers</h2>
  {table(["Broker", "URL", "Why", "Next step", "Updated UTC"], leftover_rows)}
  <h2>Mail</h2>
  {table(["Received UTC", "Status", "From", "Subject", "Mailbox", "Listing"], mail_rows)}
  <h2>Evidence chronology</h2>
  {table(["UTC", "Actor", "Broker", "Action", "Channel", "Request ID", "Result", "URL"], log_rows)}
  <footer>remove-your-data · AGPL-3.0-or-later · do not bind this to a public interface</footer>
</main>
</body>
</html>
"""


def render_csv(report: dict[str, Any]) -> str:
    fields = [
        "occurred_at_utc",
        "occurred_at_local",
        "actor",
        "person",
        "broker",
        "listing_url",
        "action",
        "channel",
        "request_id",
        "result",
        "evidence_path",
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(fields)
    for row in reversed(report["log"]):
        writer.writerow([row.get(k) or "" for k in fields])
    return buf.getvalue()


def report_from_db(db: Path) -> dict[str, Any]:
    if not db.exists():
        raise FileNotFoundError(db)
    with connect(db, readonly=True) as con:
        return load_report(con)


class Handler(BaseHTTPRequestHandler):
    db_path: Path
    server_version = "ryd-dashboard/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            report = report_from_db(self.db_path)
        except FileNotFoundError:
            self._send(404, b"database not found\n", "text/plain; charset=utf-8")
            return
        if path in ("/", "/index.html"):
            html = render_html(report, live=True)
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/report.html":
            html = render_html(report, live=False)
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/export.csv":
            self._send(
                200,
                render_csv(report).encode("utf-8"),
                "text/csv; charset=utf-8",
            )
        elif path == "/health":
            self._send(200, b"ok\n", "text/plain; charset=utf-8")
        else:
            self._send(404, b"not found\n", "text/plain; charset=utf-8")


def serve(db: Path, host: str, port: int) -> None:
    if host not in ("127.0.0.1", "localhost", "::1"):
        print(
            "Refusing to bind a PII dashboard off loopback. Use 127.0.0.1.",
            file=sys.stderr,
        )
        sys.exit(2)
    Handler.db_path = db
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Dashboard http://{host}:{port}/  (db {db})", file=sys.stderr)
    httpd.serve_forever()


def cmd_init(args: argparse.Namespace) -> int:
    db = init_workspace(args.workspace)
    print(db)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    if args.demo:
        workspace = Path(args.workspace) if args.workspace else Path("/tmp/ryd-demo")
        db = init_workspace(workspace)
        with connect(db, readonly=False) as con:
            if con.execute("SELECT COUNT(*) FROM person").fetchone()[0] == 0:
                seed_demo(con)
        serve(db, args.host, args.port)
        return 0
    if not args.workspace:
        print("--workspace is required unless --demo", file=sys.stderr)
        return 2
    db = args.workspace / "takedown.db"
    if not db.exists():
        print(f"missing {db} — run: ryd.py init --workspace {args.workspace}", file=sys.stderr)
        return 1
    serve(db, args.host, args.port)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    db = args.workspace / "takedown.db"
    report = report_from_db(db)
    out = args.out or (args.workspace / "exports" / "report.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(report, live=False), encoding="utf-8")
    print(out)
    return 0


def cmd_export_csv(args: argparse.Namespace) -> int:
    db = args.workspace / "takedown.db"
    report = report_from_db(db)
    out = args.out or (args.workspace / "exports" / "evidence-log.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_csv(report), encoding="utf-8")
    print(out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ryd",
        description="remove-your-data workspace + localhost report dashboard",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    init_p = sub.add_parser("init", help="create workspace and empty SQLite log")
    init_p.add_argument("--workspace", type=Path, required=True)
    init_p.set_defaults(func=cmd_init)

    serve_p = sub.add_parser("serve", help="localhost HTML running report")
    serve_p.add_argument("--workspace", type=Path)
    serve_p.add_argument("--demo", action="store_true", help="seed fake data and serve")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8765)
    serve_p.set_defaults(func=cmd_serve)

    exp = sub.add_parser("export", help="write a static HTML snapshot")
    exp.add_argument("--workspace", type=Path, required=True)
    exp.add_argument("--out", type=Path)
    exp.set_defaults(func=cmd_export)

    csv_p = sub.add_parser("export-csv", help="write evidence chronology CSV")
    csv_p.add_argument("--workspace", type=Path, required=True)
    csv_p.add_argument("--out", type=Path)
    csv_p.set_defaults(func=cmd_export_csv)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
