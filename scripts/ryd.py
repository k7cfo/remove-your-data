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
from urllib.parse import parse_qs, quote, urlparse

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
RELATIONSHIPS = ("self", "spouse", "partner", "child", "parent", "other")
CONSENT = ("self", "parent_of_minor", "authorized_agent", "unconfirmed")
IDENT_KINDS = (
    "name",
    "alias",
    "address",
    "prior_address",
    "city",
    "phone",
    "email",
    "dob",
    "maid",
    "vin",
    "other",
)
MAX_PEOPLE = 12
MAX_IDENTS = 40


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


def table_cols(con: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})")}


def ensure_column(con: sqlite3.Connection, table: str, name: str, spec: str) -> None:
    if name not in table_cols(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {spec}")


def migrate(con: sqlite3.Connection) -> None:
    sql = SCHEMA.read_text(encoding="utf-8")
    con.executescript(sql)
    tables = {
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "person" in tables:
        ensure_column(con, "person", "relationship", "TEXT NOT NULL DEFAULT 'self'")
        ensure_column(
            con, "person", "consent_basis", "TEXT NOT NULL DEFAULT 'self'"
        )
        ensure_column(con, "person", "active", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(con, "person", "drop_filed", "INTEGER NOT NULL DEFAULT 0")
    if "identifier" in tables:
        ensure_column(con, "identifier", "scan", "INTEGER NOT NULL DEFAULT 1")
    con.execute("DROP VIEW IF EXISTS v_evidence_chronology")
    con.execute("DROP VIEW IF EXISTS v_open_clocks")
    con.executescript(sql)
    row = con.execute(
        "SELECT value FROM config WHERE key = 'drop_filed'"
    ).fetchone()
    if row and row[0] not in ("0", "", None):
        con.execute(
            "UPDATE person SET drop_filed = 1 "
            "WHERE COALESCE(relationship, 'self') = 'self' AND drop_filed = 0"
        )
    con.commit()


def init_workspace(workspace: Path) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "evidence").mkdir(exist_ok=True)
    (workspace / "exports").mkdir(exist_ok=True)
    db = workspace / "takedown.db"
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        migrate(con)
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
          cadence_hours, anonymity_mode, household_scope, relationship,
          consent_basis, active, drop_filed, intake_complete,
          created_at_utc, notes
        ) VALUES (?, 'US', 'CA', 'America/Los_Angeles', 168, 'dedicated', 1,
                  'self', 'self', 1, 1, 1, ?, ?)
        """,
        ("Jane Q. Public", started, "Synthetic demo row. Not a real person."),
    )
    pid = int(con.execute("SELECT id FROM person").fetchone()[0])
    con.executemany(
        """
        INSERT INTO identifier (person_id, kind, value, normalized, scan)
        VALUES (?, ?, ?, ?, 1)
        """,
        [
            (pid, "name", "Jane Q. Public", "jane q public"),
            (pid, "alias", "Janie Public", "janie public"),
            (pid, "city", "Sacramento", "sacramento"),
            (pid, "address", "100 Demo Street, Sacramento, CA 95814", "100 demo street sacramento ca 95814"),
            (pid, "phone", "916-555-0142", "9165550142"),
            (pid, "email", "jane.demo@example.com", "jane.demo@example.com"),
        ],
    )
    con.execute(
        """
        INSERT INTO person (
          legal_name, residency_country, residency_region, timezone,
          cadence_hours, anonymity_mode, household_scope, relationship,
          consent_basis, active, drop_filed, intake_complete,
          created_at_utc, notes
        ) VALUES (?, 'US', 'CA', 'America/Los_Angeles', 168, 'dedicated', 1,
                  'child', 'parent_of_minor', 1, 0, 1, ?, ?)
        """,
        ("Alex Public", started, "Demo child. Parent-of-minor consent."),
    )
    kid = int(con.execute("SELECT id FROM person ORDER BY id DESC LIMIT 1").fetchone()[0])
    con.executemany(
        """
        INSERT INTO identifier (person_id, kind, value, normalized, scan)
        VALUES (?, ?, ?, ?, 1)
        """,
        [
            (kid, "name", "Alex Public", "alex public"),
            (kid, "city", "Sacramento", "sacramento"),
            (kid, "address", "100 Demo Street, Sacramento, CA 95814", "100 demo street sacramento ca 95814"),
            (kid, "email", "alex.demo@example.com", "alex.demo@example.com"),
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
    con.execute(
        "INSERT INTO config (key, value) VALUES ('sample', '1')"
    )
    con.commit()


def normalize_ident(kind: str, value: str) -> str:
    text = " ".join(value.strip().split())
    if kind == "phone":
        return "".join(c for c in text if c.isdigit())
    if kind == "email":
        return text.lower()
    return text.lower()


def list_people(con: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in con.execute(
            "SELECT * FROM person ORDER BY relationship = 'self' DESC, id ASC"
        )
    ]


def list_idents(con: sqlite3.Connection, person_id: int) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in con.execute(
            "SELECT * FROM identifier WHERE person_id = ? "
            "ORDER BY kind, id",
            (person_id,),
        )
    ]


def scan_pack(idents: list[dict[str, Any]]) -> list[str]:
    names, cities, streets, phones = [], [], [], []
    for row in idents:
        if not row.get("scan", 1):
            continue
        kind, value = row["kind"], row["value"]
        if kind in ("name", "alias"):
            names.append(value)
        elif kind == "city":
            cities.append(value)
        elif kind in ("address", "prior_address"):
            streets.append(value)
        elif kind == "phone":
            digits = normalize_ident("phone", value)
            if digits:
                phones.append(digits)
                if len(digits) == 10:
                    phones.append(f"{digits[:3]}-{digits[3:6]}-{digits[6:]}")
    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        if q and q not in seen:
            seen.add(q)
            queries.append(q)

    for name in names:
        add(f'"{name}"')
        for city in cities:
            add(f'"{name}" "{city}"')
        for street in streets:
            add(f'"{name}" "{street}"')
        for site in (
            "spokeo.com",
            "whitepages.com",
            "radaris.com",
            "truepeoplesearch.com",
            "beenverified.com",
        ):
            add(f'"{name}" site:{site}')
    for phone in phones:
        add(phone)
    return queries


def load_report(
    con: sqlite3.Connection, person_id: int | None = None
) -> dict[str, Any]:
    people = list_people(con)
    person = None
    if person_id:
        person = next((p for p in people if p["id"] == person_id), None)
    if person is None and people:
        person = next((p for p in people if p.get("relationship") == "self"), people[0])
    now = utcnow()
    counts = {status: 0 for status in STATUSES}
    total = 0
    pid = person["id"] if person else None
    if pid:
        for row in con.execute(
            "SELECT status, COUNT(*) AS n FROM listing WHERE person_id = ? GROUP BY status",
            (pid,),
        ):
            counts[row["status"]] = row["n"]
            total += row["n"]
    clocks_sql = """
        SELECT
          c.id, c.kind, c.legal_basis, c.started_at_utc, c.due_at_utc,
          c.status, c.notes, b.name AS broker, l.url AS listing_url
        FROM clock c
        LEFT JOIN broker b ON b.id = c.broker_id
        LEFT JOIN listing l ON l.id = c.listing_id
    """
    clock_args: tuple[Any, ...] = ()
    if pid:
        clocks_sql += " WHERE c.person_id = ?"
        clock_args = (pid,)
    clocks_sql += " ORDER BY c.due_at_utc ASC"
    clocks = [dict(row) for row in con.execute(clocks_sql, clock_args)]
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
    listings = []
    leftovers = []
    emails = []
    log = []
    if pid:
        listings = [
            dict(row)
            for row in con.execute(
                """
                SELECT
                  l.id, l.url, l.status, l.found_via, l.pii_shown, l.request_id,
                  l.updated_at_utc, b.name AS broker
                FROM listing l
                LEFT JOIN broker b ON b.id = l.broker_id
                WHERE l.person_id = ?
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
                """,
                (pid,),
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
                WHERE lo.open = 1 AND l.person_id = ?
                ORDER BY lo.updated_at_utc DESC
                """,
                (pid,),
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
                WHERE e.person_id = ?
                ORDER BY received_at_utc DESC
                LIMIT 50
                """,
                (pid,),
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
                WHERE person_id = ?
                ORDER BY occurred_at_utc DESC
                LIMIT 200
                """,
                (pid,),
            )
        ]
    drop_filed = bool(person and person.get("drop_filed"))
    if not drop_filed:
        cfg = con.execute(
            "SELECT value FROM config WHERE key = 'drop_filed'"
        ).fetchone()
        drop_filed = bool(cfg and cfg["value"] not in ("0", ""))
    next_due = None
    for clock in open_clocks:
        due = parse_utc(clock["due_at_utc"])
        if due and (next_due is None or due < next_due):
            next_due = due
    idents = list_idents(con, pid) if pid else []
    return {
        "generated_at": utc_iso(now),
        "person": person,
        "people": people,
        "identifiers": idents,
        "pack": scan_pack(idents),
        "counts": counts,
        "total": total,
        "open_clocks": open_clocks,
        "overdue": overdue,
        "listings": listings,
        "leftovers": leftovers,
        "emails": emails,
        "log": log,
        "drop_filed": drop_filed,
        "next_due": utc_iso(next_due) if next_due else None,
        "unhandled_mail": sum(1 for row in emails if not row["handled"]),
        "sample": bool(
            (con.execute("SELECT value FROM config WHERE key = 'sample'").fetchone() or [None])[0]
            not in (None, "0", "")
        ),
        "pending_public": counts["pending_verify"]
        + counts["pending_drop"]
        + counts["filed"]
        + counts["found"]
        + counts["leftover"]
        + counts["blocked"],
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


def human_delta(iso: str | None, now: datetime) -> str:
    dt = parse_utc(iso)
    if not dt:
        return "—"
    secs = int((dt - now).total_seconds())
    overdue = secs < 0
    secs = abs(secs)
    if secs < 90:
        return "just now" if overdue else "now"
    if secs < 3600:
        label = f"{secs // 60}m"
    elif secs < 86400:
        label = f"{secs // 3600}h"
    else:
        label = f"{secs // 86400}d"
    return f"{label} overdue" if overdue else f"in {label}"


def status_bar(counts: dict[str, int], total: int) -> str:
    if not total:
        return '<div class="bar"></div>'
    pending = (
        counts["pending_verify"]
        + counts["pending_drop"]
        + counts["filed"]
        + counts["found"]
    )
    parts = []
    for key, n in (
        ("gone", counts["gone"]),
        ("pending", pending),
        ("leftover", counts["leftover"]),
        ("blocked", counts["blocked"]),
    ):
        if n:
            parts.append(
                f'<span class="seg {key}" style="width:{100.0 * n / total:.2f}%"></span>'
            )
    return '<div class="bar">' + "".join(parts) + "</div>"


def listing_cards(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="none">No listings yet.</p>'
    bits = ['<div class="list">']
    for row in rows:
        status = row["status"]
        broker = escape(row["broker"] or "Unknown")
        url = row["url"] or ""
        meta = " · ".join(
            part for part in (row.get("pii_shown"), row.get("request_id")) if part
        )
        href = escape(url, quote=True)
        bits.append(
            f'<article class="item {escape(status)}">'
            f'<span class="rail"></span><div class="item-body">'
            f'<div class="item-head"><strong>{broker}</strong>{pill(status)}</div>'
            f'<a class="item-url" href="{href}">{escape(url)}</a>'
            f'<div class="item-meta">{escape(meta) if meta else " "}</div>'
            f"</div></article>"
        )
    bits.append("</div>")
    return "".join(bits)

def people_nav(people: list[dict[str, Any]], selected_id: int | None, current: str) -> str:
    if not people:
        return ""
    bits = ['<nav class="people">']
    for person in people:
        on = " on" if selected_id == person["id"] else ""
        skip = ""
        if person.get("consent_basis") == "unconfirmed" or not person.get("active", 1):
            skip = " skip"
        href = f"/roster?p={person['id']}" if current == "roster" else f"/?p={person['id']}"
        rel = person.get("relationship") or "self"
        bits.append(
            f'<a class="who{on}{skip}" href="{href}">{escape(person["legal_name"])}'
            f"<em>{escape(rel)}</em></a>"
        )
    extra = " on" if current == "roster" else ""
    bits.append(f'<a class="who add{extra}" href="/roster">+ family</a>')
    bits.append("</nav>")
    return "".join(bits)


def ident_line(idents: list[dict[str, Any]]) -> str:
    bits = []
    for row in idents:
        if not row.get("scan", 1):
            continue
        if row["kind"] in ("name", "dob"):
            continue
        bits.append(f'{row["kind"]} {row["value"]}')
    if not bits:
        return ""
    return '<p class="sub idents">' + escape(" · ".join(bits[:8])) + "</p>"


def render_html(report: dict[str, Any], *, live: bool, hero: bool = False) -> str:
    person = report["person"]
    now = parse_utc(report["generated_at"]) or utcnow()
    name = person["legal_name"] if person else "Takedown report"
    title = f"{name} — takedown report"
    residency = "—"
    cadence = "—"
    anonymity = "—"
    if person:
        residency = ", ".join(
            part
            for part in (person.get("residency_region"), person.get("residency_country"))
            if part
        )
        if residency == "CA, US":
            residency = "California"
        cadence = cadence_label(person.get("cadence_hours"))
        anonymity = person.get("anonymity_mode") or "—"
    counts = report["counts"]
    still = report.get("pending_public") or 0
    next_clock = (report["overdue"] or report["open_clocks"] or [None])[0]
    pulse_cls = "danger" if report["overdue"] else "ok"
    if next_clock:
        pulse_big = human_delta(next_clock["due_at_utc"], now)
        pulse_note = " · ".join(
            part
            for part in (
                next_clock.get("broker"),
                next_clock.get("kind", "").replace("_", " "),
                next_clock.get("notes"),
            )
            if part
        )
    else:
        pulse_big = "No clocks"
        pulse_note = "File a listing to start the legal timer."
    sample_chip = (
        '<span class="chip sample">sample</span>'
        if report.get("sample") and not hero
        else ""
    )
    drop_tag = (
        '<span class="tag drop">DROP filed</span>'
        if report["drop_filed"]
        else '<span class="tag">DROP not filed</span>'
    )
    empty_tag = ""
    if not person:
        empty_tag = '<span class="tag">awaiting intake</span>'
    callout = ""
    if report["overdue"]:
        first = report["overdue"][0]
        callout = (
            '<div class="callout"><strong>'
            f'{len(report["overdue"])} overdue clock'
            f'{"s" if len(report["overdue"]) != 1 else ""}</strong>'
            f'<span>{escape(first.get("broker") or "")} · '
            f'{escape((first.get("kind") or "").replace("_", " "))} · '
            f'{escape(first.get("notes") or human_delta(first["due_at_utc"], now))}'
            "</span></div>"
        )
    clock_rows = [
        [
            cell(human_delta(c["due_at_utc"], now)),
            f"<td>{pill('overdue' if c['overdue'] else c['status'])}</td>",
            cell(c["kind"]),
            cell(c["broker"]),
            cell(c["notes"]),
        ]
        for c in report["open_clocks"]
    ]
    leftover_rows = [
        [
            cell(row["broker"]),
            cell(row["url"], url=True),
            cell(row["why"]),
            cell(row["next_step"]),
        ]
        for row in report["leftovers"]
    ]
    mail_rows = [
        [
            cell(row["received_at_utc"]),
            f"<td>{pill('open' if not row['handled'] else 'done')}</td>",
            cell(row["from_domain"]),
            cell(row["subject"]),
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
            cell(row["result"]),
            cell(row["listing_url"], url=True),
        ]
        for row in report["log"]
    ]
    refresh = (
        '<meta http-equiv="refresh" content="30">'
        if live and not hero
        else ""
    )
    links = (
        '<a href="/roster">roster</a> · <a href="/export.csv">CSV</a> · <a href="/report.html">snapshot</a>'
        if live
        else "<span>snapshot</span>"
    )
    who = "" if hero else people_nav(
        report.get("people") or [],
        person["id"] if person else None,
        "report",
    )
    scans = ident_line(report.get("identifiers") or [])
    css = (Path(__file__).resolve().parent / "dashboard.css").read_text(
        encoding="utf-8"
    )
    body_cls = "shot" if hero else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}
<title>{escape(title)}</title>
<style>{css}</style>
</head>
<body class="{body_cls}">
<div class="shell">
  <nav class="top">
    <div class="brand"><span class="mark"></span>remove-your-data</div>
    <div class="top-meta">
      {sample_chip}
      <span class="chip">127.0.0.1</span>
      <span>{escape(report["generated_at"])}</span>
      {links}
    </div>
  </nav>
  {who}
  <section class="masthead">
    <div>
      <p class="eyebrow">Subject</p>
      <h1>{escape(name)}</h1>
      <p class="sub">{escape(residency)} · {escape(anonymity)} · {escape(cadence)}</p>
      {scans}
      <div class="tags">{drop_tag}{empty_tag}</div>
    </div>
    <div class="panel">
      <p class="eyebrow">Indexed listings</p>
      <p class="big"><b>{counts["gone"]}</b><span> gone</span> &nbsp;<b>{still}</b><span> still public</span></p>
      {status_bar(counts, report["total"])}
      <div class="legend">
        <span><i class="gone"></i>gone {counts["gone"]}</span>
        <span><i class="pending"></i>pending {counts["pending_verify"] + counts["pending_drop"] + counts["filed"] + counts["found"]}</span>
        <span><i class="leftover"></i>leftover {counts["leftover"]}</span>
        <span><i class="blocked"></i>blocked {counts["blocked"]}</span>
      </div>
    </div>
    <div class="panel {pulse_cls}">
      <p class="eyebrow">Next legal clock</p>
      <p class="big">{escape(pulse_big)}</p>
      <p class="pulse-note">{escape(pulse_note)}</p>
    </div>
  </section>
  {callout}
  <h2>Listings</h2>
  {listing_cards(report["listings"])}
  <div class="below">
    <h2>Open clocks</h2>
    {table(["Due", "Status", "Kind", "Broker", "Notes"], clock_rows)}
    <h2>Leftovers</h2>
    {table(["Broker", "URL", "Why", "Next step"], leftover_rows)}
    <h2>Mail</h2>
    {table(["Received UTC", "Status", "From", "Subject", "Listing"], mail_rows)}
    <h2>Evidence chronology</h2>
    {table(["UTC", "Actor", "Broker", "Action", "Result", "URL"], log_rows)}
  </div>
  <footer>AGPL-3.0-or-later · local legal log · not legal advice · do not bind this to a public interface</footer>
</div>
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


def add_identifier(con: sqlite3.Connection, person_id: int, kind: str, value: str) -> None:
    kind = kind if kind in IDENT_KINDS else "other"
    value = value.strip()
    if not value:
        raise ValueError("Identifier value required.")
    n = con.execute(
        "SELECT COUNT(*) FROM identifier WHERE person_id = ?", (person_id,)
    ).fetchone()[0]
    if n >= MAX_IDENTS:
        raise ValueError("Cap is 40 identifiers per person.")
    norm = normalize_ident(kind, value)
    if not norm:
        raise ValueError("Could not normalize that value.")
    if kind == "email":
        taken = con.execute(
            "SELECT person_id FROM identifier WHERE kind = 'email' AND normalized = ?",
            (norm,),
        ).fetchone()
        if taken and int(taken[0]) != person_id:
            raise ValueError("That email is already used by someone in this household. Brokers treat one address as one person.")
    try:
        con.execute(
            """
            INSERT INTO identifier (person_id, kind, value, normalized, scan)
            VALUES (?, ?, ?, ?, 1)
            """,
            (person_id, kind, value, norm),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("Already on this person.") from exc


def add_family_member(con: sqlite3.Connection, fields: dict[str, str]) -> int:
    n = con.execute("SELECT COUNT(*) FROM person").fetchone()[0]
    if n >= MAX_PEOPLE:
        raise ValueError("Household cap is 12 people.")
    name = fields.get("legal_name", "").strip()
    if not name:
        raise ValueError("Name required.")
    rel = fields.get("relationship", "other")
    if rel not in RELATIONSHIPS or rel == "self":
        rel = "other"
    consent = fields.get("consent_basis", "unconfirmed")
    if consent not in CONSENT or consent == "self":
        consent = "unconfirmed"
    if rel == "child" and consent == "unconfirmed":
        consent = "parent_of_minor"
    primary = con.execute(
        "SELECT * FROM person WHERE relationship = 'self' ORDER BY id LIMIT 1"
    ).fetchone()
    country = (primary["residency_country"] if primary else "US") or "US"
    region = primary["residency_region"] if primary else None
    tz = primary["timezone"] if primary else "UTC"
    cadence = primary["cadence_hours"] if primary else 168
    anon = primary["anonymity_mode"] if primary else "dedicated"
    con.execute(
        """
        INSERT INTO person (
          legal_name, residency_country, residency_region, timezone,
          cadence_hours, anonymity_mode, household_scope, relationship,
          consent_basis, active, drop_filed, intake_complete, created_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 1, 0, 1, ?)
        """,
        (name, country, region, tz, cadence, anon, rel, consent, utc_iso()),
    )
    pid = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
    add_identifier(con, pid, "name", name)
    return pid


def apply_roster_post(con: sqlite3.Connection, fields: dict[str, str]) -> str:
    action = fields.get("action", "")
    if action == "add_ident":
        pid = int(fields.get("person_id", "0"))
        add_identifier(con, pid, fields.get("kind", "alias"), fields.get("value", ""))
        return f"/roster?p={pid}"
    if action == "delete_ident":
        iid = int(fields.get("ident_id", "0"))
        row = con.execute(
            "SELECT person_id FROM identifier WHERE id = ?", (iid,)
        ).fetchone()
        con.execute("DELETE FROM identifier WHERE id = ?", (iid,))
        return f"/roster?p={row['person_id']}" if row else "/roster"
    if action == "toggle_scan":
        iid = int(fields.get("ident_id", "0"))
        con.execute(
            "UPDATE identifier SET scan = CASE scan WHEN 1 THEN 0 ELSE 1 END WHERE id = ?",
            (iid,),
        )
        row = con.execute(
            "SELECT person_id FROM identifier WHERE id = ?", (iid,)
        ).fetchone()
        return f"/roster?p={row['person_id']}" if row else "/roster"
    if action == "add_person":
        pid = add_family_member(con, fields)
        return f"/roster?p={pid}"
    if action == "set_consent":
        pid = int(fields.get("person_id", "0"))
        consent = fields.get("consent_basis", "unconfirmed")
        if consent not in CONSENT:
            consent = "unconfirmed"
        rel = con.execute(
            "SELECT relationship FROM person WHERE id = ?", (pid,)
        ).fetchone()
        if rel and rel["relationship"] != "self" and consent == "self":
            raise ValueError("Only the primary subject uses self-consent. Use authorized agent or parent of minor.")
        con.execute(
            "UPDATE person SET consent_basis = ? WHERE id = ?", (consent, pid)
        )
        return f"/roster?p={pid}"
    raise ValueError("Unknown roster action.")


def render_roster(report: dict[str, Any], flash: str = "") -> str:
    person = report["person"]
    pid = person["id"] if person else 0
    css = (Path(__file__).resolve().parent / "dashboard.css").read_text(
        encoding="utf-8"
    )
    who = people_nav(report.get("people") or [], pid or None, "roster")
    groups: dict[str, list[dict[str, Any]]] = {k: [] for k in IDENT_KINDS}
    for row in report.get("identifiers") or []:
        groups.setdefault(row["kind"], []).append(row)
    blocks = []
    for kind in IDENT_KINDS:
        rows = groups.get(kind) or []
        items = []
        for row in rows:
            off = "" if row.get("scan", 1) else " off"
            items.append(
                '<li class="ident{off}">'
                "<span>{val}</span>"
                '<form method="post" action="/roster" class="inline">'
                '<input type="hidden" name="action" value="toggle_scan">'
                '<input type="hidden" name="ident_id" value="{iid}">'
                '<button type="submit">{scan}</button>'
                "</form>"
                '<form method="post" action="/roster" class="inline">'
                '<input type="hidden" name="action" value="delete_ident">'
                '<input type="hidden" name="ident_id" value="{iid}">'
                '<button type="submit" class="danger">remove</button>'
                "</form>"
                "</li>".format(
                    off=off,
                    val=escape(row["value"]),
                    iid=row["id"],
                    scan="scanning" if row.get("scan", 1) else "paused",
                )
            )
        empty = '<li class="muted">None</li>'
        blocks.append(
            f'<div class="ident-group"><h3>{escape(kind.replace("_", " "))}</h3>'
            f"<ul>{''.join(items) or empty}</ul></div>"
        )
    kind_opts = "".join(
        f'<option value="{k}">{k.replace("_", " ")}</option>' for k in IDENT_KINDS
        if k != "name"
    )
    rel_opts = "".join(
        f'<option value="{r}">{r.replace("_", " ")}</option>'
        for r in RELATIONSHIPS
        if r != "self"
    )
    consent_opts = "".join(
        f'<option value="{c}"{" selected" if person and person.get("consent_basis")==c else ""}>{c.replace("_", " ")}</option>'
        for c in CONSENT
    )
    flash_html = f'<p class="callout"><strong>{escape(flash)}</strong></p>' if flash else ""
    consent_note = ""
    if person and person.get("consent_basis") == "unconfirmed":
        consent_note = (
            '<p class="callout"><strong>Not scanned.</strong>'
            "<span>Set consent: they authorized you, or you are the parent of a minor. "
            "Do not file as someone who did not agree.</span></p>"
        )
    name = person["legal_name"] if person else "Roster"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Roster — {escape(name)}</title>
<style>{css}</style>
</head>
<body>
<div class="shell">
  <nav class="top">
    <div class="brand"><span class="mark"></span>remove-your-data</div>
    <div class="top-meta">
      <a href="/">report</a>
      <span class="chip">127.0.0.1</span>
    </div>
  </nav>
  {who}
  <p class="eyebrow">Household roster</p>
  <h1>{escape(name)}</h1>
  <p class="sub">Aliases, addresses, and phones here drive the search pack. Each family member is a separate legal person: own DROP, own verify email, own listings.</p>
  {flash_html}{consent_note}
  <form method="post" action="/roster" class="panel form-row">
    <input type="hidden" name="action" value="set_consent">
    <input type="hidden" name="person_id" value="{pid}">
    <label>Consent
      <select name="consent_basis">{consent_opts}</select>
    </label>
    <button type="submit">Save</button>
  </form>
  <h2>Scan identifiers</h2>
  <div class="ident-grid">{"".join(blocks)}</div>
  <form method="post" action="/roster" class="panel form-row">
    <input type="hidden" name="action" value="add_ident">
    <input type="hidden" name="person_id" value="{pid}">
    <label>Kind <select name="kind">{kind_opts}</select></label>
    <label class="grow">Value <input name="value" required maxlength="200" placeholder="alias, street, phone, email"></label>
    <button type="submit">Add</button>
  </form>
  <h2>Add family member</h2>
  <form method="post" action="/roster" class="panel form-row">
    <input type="hidden" name="action" value="add_person">
    <label class="grow">Legal name <input name="legal_name" required maxlength="120"></label>
    <label>Relationship <select name="relationship">{rel_opts}</select></label>
    <label>Consent
      <select name="consent_basis">
        <option value="parent_of_minor">parent of minor</option>
        <option value="authorized_agent">they authorized me</option>
        <option value="unconfirmed">not yet — do not scan</option>
      </select>
    </label>
    <button type="submit">Add person</button>
  </form>
  <footer>One person per DROP. Distinct verify email per person. Loopback only.</footer>
</div>
</body>
</html>
"""


def report_from_db(db: Path, person_id: int | None = None) -> dict[str, Any]:
    if not db.exists():
        raise FileNotFoundError(db)
    with connect(db, readonly=True) as con:
        return load_report(con, person_id)


def read_post(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length > 64_000:
        raise ValueError("POST too large")
    raw = handler.rfile.read(length).decode("utf-8", "replace")
    return {k: (v[0] if v else "") for k, v in parse_qs(raw, keep_blank_values=True).items()}


def person_query(qs: dict[str, list[str]]) -> int | None:
    raw = (qs.get("p") or [None])[0]
    try:
        return int(raw) if raw else None
    except (TypeError, ValueError):
        return None


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

    def _redirect(self, location: str) -> None:
        body = b""
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        hero = (qs.get("hero") or ["0"])[0] in ("1", "true", "yes")
        pid = person_query(qs)
        try:
            report = report_from_db(self.db_path, pid)
        except FileNotFoundError:
            self._send(404, b"database not found\n", "text/plain; charset=utf-8")
            return
        if path in ("/", "/index.html"):
            html = render_html(report, live=True, hero=hero)
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/report.html":
            html = render_html(report, live=False, hero=hero)
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/roster":
            flash = (qs.get("err") or qs.get("ok") or [""])[0]
            html = render_roster(report, flash=flash)
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

    def do_POST(self) -> None:  # noqa: N802
        if self.client_address[0] not in ("127.0.0.1", "::1"):
            self._send(403, b"loopback only\n", "text/plain; charset=utf-8")
            return
        parsed = urlparse(self.path)
        if parsed.path != "/roster":
            self._send(404, b"not found\n", "text/plain; charset=utf-8")
            return
        try:
            fields = read_post(self)
        except ValueError as exc:
            self._redirect("/roster?err=" + quote(str(exc)))
            return
        try:
            with connect(self.db_path, readonly=False) as con:
                dest = apply_roster_post(con, fields)
                con.commit()
        except (ValueError, sqlite3.Error) as exc:
            self._redirect("/roster?err=" + quote(str(exc)))
            return
        self._redirect(dest)


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


def cmd_add_person(args: argparse.Namespace) -> int:
    db = args.workspace / "takedown.db"
    if not db.exists():
        print("missing workspace — run init first", file=sys.stderr)
        return 1
    try:
        with connect(db, readonly=False) as con:
            pid = add_family_member(
                con,
                {
                    "legal_name": args.name,
                    "relationship": args.relationship,
                    "consent_basis": args.consent,
                },
            )
            con.commit()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(pid)
    return 0


def cmd_add_ident(args: argparse.Namespace) -> int:
    db = args.workspace / "takedown.db"
    try:
        with connect(db, readonly=False) as con:
            add_identifier(con, args.person_id, args.kind, args.value)
            con.commit()
    except (ValueError, sqlite3.Error) as exc:
        print(exc, file=sys.stderr)
        return 1
    print("ok")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    db = args.workspace / "takedown.db"
    with connect(db, readonly=True) as con:
        people = list_people(con)
        targets = people
        if args.person_id:
            targets = [p for p in people if p["id"] == args.person_id]
        for person in targets:
            if not person.get("active", 1):
                continue
            if person.get("consent_basis") == "unconfirmed":
                print(f"# skip {person['legal_name']} (unconfirmed consent)", file=sys.stderr)
                continue
            print(f"# {person['id']} {person['legal_name']} ({person.get('relationship')})")
            for q in scan_pack(list_idents(con, person["id"])):
                print(q)
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

    ap = sub.add_parser("add-person", help="add a family member to the roster")
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--relationship", default="other", choices=[r for r in RELATIONSHIPS if r != "self"])
    ap.add_argument("--consent", default="unconfirmed", choices=[c for c in CONSENT if c != "self"])
    ap.set_defaults(func=cmd_add_person)

    ai = sub.add_parser("add-ident", help="add alias/address/phone/email to a person")
    ai.add_argument("--workspace", type=Path, required=True)
    ai.add_argument("--person-id", type=int, required=True)
    ai.add_argument("--kind", required=True, choices=IDENT_KINDS)
    ai.add_argument("--value", required=True)
    ai.set_defaults(func=cmd_add_ident)

    pk = sub.add_parser("pack", help="print search queries for consented people")
    pk.add_argument("--workspace", type=Path, required=True)
    pk.add_argument("--person-id", type=int)
    pk.set_defaults(func=cmd_pack)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
