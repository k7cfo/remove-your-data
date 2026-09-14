# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
import threading
import unittest
from html.parser import HTMLParser

import test_ryd as support


ryd = support.ryd
REGIONS = ("NA", "SA", "EU", "AF", "AS", "OC", "UNKNOWN")
OLD_DATE = "2001-01-01T00:00:00Z"


def counts(**regions: tuple[int, int]) -> dict:
    return {
        region: dict(zip(("exposed", "gone"), regions.get(region, (0, 0))))
        for region in REGIONS
    }


def add_broker(con: sqlite3.Connection, region: str = "UNKNOWN", name: str = "Synthetic broker") -> int:
    return con.execute(
        "INSERT INTO broker (name, operator_region) VALUES (?, ?)", (name, region)
    ).lastrowid


def add_listing(con: sqlite3.Connection, person: int, broker: int | None = None, status: str = "found") -> int:
    serial = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM listing").fetchone()[0]
    return con.execute(
        """
        INSERT INTO listing (person_id, broker_id, url, status, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (person, broker, f"https://synthetic-listing.example/{serial}", status, OLD_DATE, OLD_DATE),
    ).lastrowid


def stamp_latest(con: sqlite3.Connection, listing: int, at: str) -> None:
    con.execute(
        "UPDATE listing_status_event SET occurred_at_utc = ? WHERE id = "
        "(SELECT MAX(id) FROM listing_status_event WHERE listing_id = ?)",
        (at, listing),
    )


def change_status(con: sqlite3.Connection, listing: int, status: str, at: str) -> None:
    con.execute("UPDATE listing SET status = ? WHERE id = ?", (status, listing))
    stamp_latest(con, listing, at)


def instant(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


class Element:
    def __init__(self, tag: str, attrs: list[tuple[str, str | None]], parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []

    def text(self) -> str:
        return "".join(child if isinstance(child, str) else child.text() for child in self.children)

    def descendants(self, tag: str | None = None):
        for child in self.children:
            if isinstance(child, Element):
                if tag is None or child.tag == tag:
                    yield child
                yield from child.descendants(tag)

    def hidden(self) -> bool:
        return "hidden" in self.attrs or (self.parent is not None and self.parent.hidden())


class Page(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.root = Element("document", [])
        self.current = self.root
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in self.VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.current.children.append(Element(tag, attrs, self.current))

    def handle_endtag(self, tag):
        node = self.current
        while node.parent is not None:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        self.current.children.append(data)

    def by_id(self, identifier: str) -> Element:
        matches = [node for node in self.root.descendants() if node.attrs.get("id") == identifier]
        if len(matches) != 1:
            raise AssertionError(f"Expected exactly one #{identifier}, got {len(matches)}")
        return matches[0]

    def payload(self) -> dict:
        node = self.by_id("landscape-data")
        if node.tag != "script" or node.attrs.get("type") != "application/json":
            raise AssertionError("Landscape data must be an inert JSON script")
        return json.loads(node.text())


class LandscapeTests(support.WorkspaceCase):
    def test_history_preserves_earlier_states_through_removal_and_relisting(self) -> None:
        with self.connect() as con:
            person = support.add_primary(con)
            broker = add_broker(con, "EU")
            first = add_listing(con, person, broker)
            stamp_latest(con, first, "2026-01-01T00:00:00Z")
            change_status(con, first, "gone", "2026-01-03T00:00:00Z")
            second = add_listing(con, person, broker, "blocked")
            stamp_latest(con, second, "2026-01-02T00:00:00Z")
            before = ryd.load_landscape(con, person)
            change_status(con, first, "found", "2026-01-04T00:00:00Z")
            after = ryd.load_landscape(con, person)
        self.assertEqual([instant(frame["at"]) for frame in after["history"]], [
            instant(f"2026-01-0{day}T00:00:00Z") for day in range(1, 5)
        ])
        self.assertEqual([frame["counts"] for frame in after["history"]], [
            counts(EU=(1, 0)), counts(EU=(2, 0)), counts(EU=(1, 1)), counts(EU=(2, 0)),
        ])
        self.assertEqual(after["history"][:3], before["history"])
        self.assertEqual(before["current"], counts(EU=(1, 1)))
        self.assertEqual(after["current"], counts(EU=(2, 0)))

    def test_simultaneous_events_coalesce_by_utc_instant_and_last_id_wins(self) -> None:
        with self.connect() as con:
            person = support.add_primary(con)
            broker = add_broker(con, "NA")
            first = add_listing(con, person, broker)
            second = add_listing(con, person, broker)
            con.execute("DELETE FROM listing_status_event")
            con.executemany(
                "INSERT INTO listing_status_event (id, listing_id, status, occurred_at_utc) VALUES (?, ?, ?, ?)",
                [
                    (30, first, "gone", "2026-02-01T02:00:00+02:00"),
                    (10, first, "found", "2026-02-01T00:00:00Z"),
                    (20, second, "found", "2026-01-31T19:00:00-05:00"),
                    (40, first, "found", "2026-02-01T00:00:00.500Z"),
                    (50, second, "gone", "2026-02-01T00:00:00.050+00:00"),
                ],
            )
            result = ryd.load_landscape(con, person)
        self.assertEqual([instant(frame["at"]) for frame in result["history"]], [
            instant("2026-02-01T00:00:00Z"),
            instant("2026-02-01T00:00:00.050Z"),
            instant("2026-02-01T00:00:00.500Z"),
        ])
        self.assertTrue(all(frame["at"].endswith("Z") for frame in result["history"]))
        self.assertEqual([frame["counts"] for frame in result["history"]], [
            counts(NA=(1, 1)), counts(NA=(0, 2)), counts(NA=(1, 1)),
        ])
        # Current is the listing snapshot, not a replay of manually edited history.
        self.assertEqual(result["current"], counts(NA=(2, 0)))

    def test_person_selection_never_aggregates_other_people(self) -> None:
        with self.connect() as con:
            first = support.add_primary(con)
            second = support.add_primary(con, name="Other synthetic person")
            broker = add_broker(con, "AS")
            own = add_listing(con, first, broker)
            other = add_listing(con, second, broker, "gone")
            stamp_latest(con, own, "2026-01-01T00:00:00Z")
            stamp_latest(con, other, "2026-01-02T00:00:00Z")
            for person, expected, at in (
                (first, counts(AS=(1, 0)), "2026-01-01T00:00:00Z"),
                (second, counts(AS=(0, 1)), "2026-01-02T00:00:00Z"),
            ):
                with self.subTest(person=person):
                    result = ryd.load_landscape(con, person)
                    self.assertEqual(result["current"], expected)
                    self.assertEqual([frame["counts"] for frame in result["history"]], [expected])
                    self.assertEqual(instant(result["history"][0]["at"]), instant(at))
            for person in (None, 999999):
                with self.subTest(person=person):
                    self.assertEqual(ryd.load_landscape(con, person), {"current": counts(), "history": []})

    def test_unknown_metadata_is_not_guessed_from_broker_names_or_urls(self) -> None:
        with self.connect() as con:
            person = support.add_primary(con)
            broker = con.execute(
                "INSERT INTO broker (name, optout_url) VALUES ('European synthetic operator', 'https://synthetic.example.de/optout')"
            ).lastrowid
            add_listing(con, person, broker)
            add_listing(con, person, None, "gone")
            self.assertEqual(ryd.load_landscape(con, person)["current"], counts(UNKNOWN=(1, 1)))
            for invalid in ("US", "Europe", "eu", "", None):
                with self.subTest(region=invalid), self.assertRaises(sqlite3.IntegrityError):
                    con.execute("UPDATE broker SET operator_region = ? WHERE id = ?", (invalid, broker))
            # Defend reads of damaged/imported metadata as well as validated writes.
            con.execute("PRAGMA ignore_check_constraints = ON")
            con.execute("UPDATE broker SET operator_region = 'US' WHERE id = ?", (broker,))
            con.execute("PRAGMA ignore_check_constraints = OFF")
            con.commit()
            con.execute("PRAGMA foreign_keys = OFF")
            con.execute("UPDATE listing SET broker_id = 999999 WHERE broker_id IS NULL")
            result = ryd.load_landscape(con, person)
        self.assertEqual(result["current"], counts(UNKNOWN=(1, 1)))
        self.assertEqual(result["history"][-1]["counts"], counts(UNKNOWN=(1, 1)))

    def test_every_non_gone_status_remains_exposed(self) -> None:
        statuses = ("found", "filed", "pending_verify", "pending_drop", "gone", "leftover", "blocked")
        with self.connect() as con:
            person = support.add_primary(con)
            broker = add_broker(con, "AF")
            listing = add_listing(con, person, broker)
            stamp_latest(con, listing, "2026-03-01T00:00:00Z")
            for day, status in enumerate(statuses, 1):
                if day != 1:
                    change_status(con, listing, status, f"2026-03-0{day}T00:00:00Z")
                expected = counts(AF=(0, 1) if status == "gone" else (1, 0))
                with self.subTest(status=status):
                    result = ryd.load_landscape(con, person)
                    self.assertEqual(result["current"], expected)
                    self.assertEqual(result["history"][-1]["counts"], expected)

    def test_direct_workspace_sql_logs_only_real_status_changes_at_recording_time(self) -> None:
        with self.connect() as con:
            person = support.add_primary(con)
            con.commit()
        # No ryd connection or write helper participates in recording these events.
        with sqlite3.connect(self.db) as raw:
            lower = raw.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now')").fetchone()[0]
            listing = add_listing(raw, person)
            raw.execute("UPDATE listing SET status = 'found', updated_at_utc = ? WHERE id = ?", (OLD_DATE, listing))
            raw.execute("UPDATE listing SET status = 'gone' WHERE id = ?", (listing,))
            raw.execute("UPDATE listing SET status = 'gone', pii_shown = 'synthetic note' WHERE id = ?", (listing,))
            raw.execute("UPDATE listing SET status = 'found' WHERE id = ?", (listing,))
            upper = raw.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now')").fetchone()[0]
            events = raw.execute(
                "SELECT status, occurred_at_utc FROM listing_status_event WHERE listing_id = ? ORDER BY id", (listing,)
            ).fetchall()
        self.assertEqual([status for status, _ in events], ["found", "gone", "found"])
        for _, at in events:
            self.assertLessEqual(instant(lower), instant(at))
            self.assertLessEqual(instant(at), instant(upper))
        with self.connect() as con:
            self.assertEqual(ryd.load_landscape(con, person)["current"], counts(UNKNOWN=(1, 0)))

    def test_legacy_migration_records_baseline_now_and_is_idempotent(self) -> None:
        legacy = self.workspace / "legacy.db"
        with ryd.connect(legacy, readonly=False) as con:
            con.executescript("""
                CREATE TABLE person (
                    id INTEGER PRIMARY KEY, legal_name TEXT NOT NULL,
                    residency_country TEXT NOT NULL, residency_region TEXT,
                    timezone TEXT NOT NULL DEFAULT 'UTC', cadence_hours INTEGER NOT NULL DEFAULT 168,
                    anonymity_mode TEXT NOT NULL DEFAULT 'dedicated', household_scope INTEGER NOT NULL DEFAULT 0,
                    relationship TEXT NOT NULL DEFAULT 'self', consent_basis TEXT NOT NULL DEFAULT 'self',
                    active INTEGER NOT NULL DEFAULT 1, drop_filed INTEGER NOT NULL DEFAULT 0,
                    intake_complete INTEGER NOT NULL DEFAULT 0, created_at_utc TEXT NOT NULL, notes TEXT
                );
                CREATE TABLE broker (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, family TEXT,
                    optout_url TEXT, channel TEXT, notes TEXT
                );
                CREATE TABLE listing (
                    id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES person(id),
                    broker_id INTEGER REFERENCES broker(id), url TEXT NOT NULL, found_via TEXT, pii_shown TEXT,
                    status TEXT NOT NULL DEFAULT 'found' CHECK(status IN
                      ('found', 'filed', 'pending_verify', 'pending_drop', 'gone', 'leftover', 'blocked')),
                    email_used TEXT, request_id TEXT, created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL, UNIQUE(person_id, url)
                );
                INSERT INTO person (id, legal_name, residency_country, created_at_utc)
                    VALUES (1, 'Synthetic legacy person', 'US', '2001-01-01T00:00:00Z');
                INSERT INTO broker (id, name) VALUES (1, 'Synthetic legacy broker');
                INSERT INTO listing (id, person_id, broker_id, url, status, created_at_utc, updated_at_utc)
                    VALUES (1, 1, 1, 'https://legacy.example/one', 'gone', '2001-01-01T00:00:00Z', '2002-01-01T00:00:00Z');
                INSERT INTO listing (id, person_id, url, status, created_at_utc, updated_at_utc)
                    VALUES (2, 1, 'https://legacy.example/two', 'blocked', '2003-01-01T00:00:00Z', '2004-01-01T00:00:00Z');
            """)
            self.assertEqual(
                ryd.load_landscape(con, 1),
                {"current": counts(UNKNOWN=(1, 1)), "history": []},
            )
            lower = con.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now')").fetchone()[0]
            ryd.migrate(con)
            upper = con.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now')").fetchone()[0]
            baseline = [tuple(row) for row in con.execute("SELECT * FROM listing_status_event ORDER BY id")]
            events = con.execute("SELECT listing_id, status, occurred_at_utc FROM listing_status_event ORDER BY listing_id").fetchall()
            self.assertEqual([(row[0], row[1]) for row in events], [(1, "gone"), (2, "blocked")])
            for row in events:
                self.assertLessEqual(instant(lower), instant(row[2]))
                self.assertLessEqual(instant(row[2]), instant(upper))
            self.assertEqual(ryd.load_landscape(con, 1)["current"], counts(UNKNOWN=(1, 1)))
            self.assertEqual(ryd.load_landscape(con, 1)["history"][-1]["counts"], counts(UNKNOWN=(1, 1)))
            ryd.migrate(con)
            self.assertEqual([tuple(row) for row in con.execute("SELECT * FROM listing_status_event ORDER BY id")], baseline)
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("UPDATE broker SET operator_region = 'US'")
            change_status(con, 1, "found", "2026-04-01T00:00:00Z")
            add_listing(con, 1, 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM listing_status_event").fetchone()[0], 4)
            self.assertEqual(ryd.load_landscape(con, 1)["current"], counts(UNKNOWN=(3, 0)))

    def test_script_json_cannot_break_out_and_roundtrips_unicode(self) -> None:
        value = {"payload": '</script><script id="injected">alert(1)</script><>&\u2028\u2029', "nested": ["é", 1, None]}
        encoded = ryd.script_json(value)
        self.assertEqual(json.loads(encoded), value)
        for character in ("<", ">", "&", "\u2028", "\u2029"):
            self.assertNotIn(character, encoded)
        page = Page('<script type="application/json" id="landscape-data">' + encoded + '</script><p id="after">Safe</p>')
        self.assertEqual(page.payload(), value)
        self.assertEqual(len(list(page.root.descendants("script"))), 1)
        self.assertEqual(page.by_id("after").text(), "Safe")

    def test_visualization_payload_has_only_region_counts_and_times_not_private_records(self) -> None:
        sentinels = {
            "name": 'PII_NAME_SENTINEL</script><script id="pii-injected">x</script>',
            "alias": "PII_ALIAS_SENTINEL", "address": "PII_ADDRESS_SENTINEL",
            "phone": "2025550147", "email": "PII_EMAIL_SENTINEL@example.invalid",
            "person_notes": "PERSON_NOTES_SENTINEL", "broker": "BROKER_NAME_SENTINEL",
            "broker_notes": "BROKER_NOTES_SENTINEL", "broker_url": "https://broker-sentinel.example/optout",
            "url": "https://listing-sentinel.example/private", "pii": "LISTING_PII_SENTINEL",
            "found_via": "FOUND_VIA_SENTINEL", "request": "REQUEST_ID_SENTINEL",
            "result": "ACTION_RESULT_SENTINEL", "evidence": "evidence/EVIDENCE_PATH_SENTINEL.png",
        }
        with self.connect() as con:
            person = support.add_primary(con, name=sentinels["name"])
            for kind in ("alias", "address", "phone", "email"):
                ryd.add_identifier(con, person, kind, sentinels[kind])
            con.execute("UPDATE person SET notes = ? WHERE id = ?", (sentinels["person_notes"], person))
            broker = add_broker(con, "OC", sentinels["broker"])
            con.execute("UPDATE broker SET notes = ?, optout_url = ? WHERE id = ?", (sentinels["broker_notes"], sentinels["broker_url"], broker))
            listing = add_listing(con, person, broker)
            con.execute(
                "UPDATE listing SET url = ?, pii_shown = ?, found_via = ?, email_used = ?, request_id = ? WHERE id = ?",
                (sentinels["url"], sentinels["pii"], sentinels["found_via"], sentinels["email"], sentinels["request"], listing),
            )
            con.execute(
                "INSERT INTO action_log (person_id, listing_id, broker_id, actor, action, request_id, result, evidence_path, listing_url, occurred_at_utc, occurred_at_local) "
                "VALUES (?, ?, ?, 'agent', 'synthetic', ?, ?, ?, ?, ?, ?)",
                (person, listing, broker, sentinels["request"], sentinels["result"], sentinels["evidence"], sentinels["url"], OLD_DATE, OLD_DATE),
            )
            html = ryd.render_landscape(ryd.load_report(con, person))
        page = Page(html)
        payload = page.payload()
        serialized = json.dumps(payload, ensure_ascii=False)
        for sentinel in sentinels.values():
            self.assertNotIn(sentinel, serialized)
        self.assertEqual(set(payload), {"current", "history"})
        self.assertEqual(payload["current"], counts(OC=(1, 0)))
        for frame in payload["history"]:
            self.assertEqual(set(frame), {"at", "counts"})
            instant(frame["at"])
        for buckets in [payload["current"]] + [frame["counts"] for frame in payload["history"]]:
            self.assertEqual(set(buckets), set(REGIONS))
            for bucket in buckets.values():
                self.assertEqual(set(bucket), {"exposed", "gone"})
                for value in bucket.values():
                    self.assertIs(type(value), int)
                    self.assertGreaterEqual(value, 0)
        self.assertFalse(any(node.attrs.get("id") == "pii-injected" for node in page.root.descendants()))

    def test_standalone_html_is_offline_and_useful_without_javascript(self) -> None:
        with self.connect() as con:
            person = support.add_primary(con)
            broker = add_broker(con, "SA")
            add_listing(con, person, broker)
            add_listing(con, person, broker, "gone")
            page = Page(ryd.render_landscape(ryd.load_report(con, person)))
        table = page.by_id("landscape-counts")
        self.assertEqual(table.tag, "table")
        self.assertFalse(table.hidden())
        rows = {row.attrs["data-region"]: row for row in table.descendants("tr") if "data-region" in row.attrs}
        self.assertEqual(set(rows), set(REGIONS))
        for region, row in rows.items():
            cells = {cell.attrs.get("class"): cell.text().strip() for cell in row.descendants("td")}
            self.assertEqual(cells["exposed"], "1" if region == "SA" else "0")
            self.assertEqual(cells["gone"], "1" if region == "SA" else "0")
            self.assertTrue(any(cell.attrs.get("scope") == "row" and cell.text().strip() for cell in row.descendants("th")))
        marker = next(node for node in page.root.descendants("g") if node.attrs.get("data-region") == "SA")
        self.assertFalse(marker.hidden())
        circle = next(marker.descendants("circle"))
        self.assertGreater(float(circle.attrs["r"]), 0)
        self.assertTrue(any(node.text().strip() for node in circle.descendants("title")))
        for node in page.root.descendants():
            self.assertNotEqual(node.tag, "base")
            if node.tag == "meta":
                self.assertNotEqual(node.attrs.get("http-equiv", "").lower(), "refresh")
            if node.tag == "a":
                self.assertTrue(node.attrs.get("href", "").startswith(("/", "#")), node.attrs)
            for attr in ("src", "srcset", "poster", "data", "xlink:href"):
                if attr in node.attrs:
                    self.assertTrue(node.attrs[attr].startswith(("data:", "#")), node.attrs)
            if node.tag in ("link", "use", "image") and "href" in node.attrs:
                self.assertTrue(node.attrs["href"].startswith(("data:", "#")), node.attrs)
        styles = "\n".join(node.text() for node in page.root.descendants("style"))
        self.assertNotRegex(styles, r"(?i)@import\b")
        for resource in re.findall(r"url\(\s*['\"]?([^)'\"]+)", styles, re.IGNORECASE):
            self.assertTrue(resource.startswith(("data:", "#")), resource)
        scripts = "\n".join(node.text() for node in page.root.descendants("script") if node.attrs.get("type") != "application/json")
        self.assertNotRegex(scripts, r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts)\b|\bimport\s*\(")
        self.assertNotRegex(scripts, r"\b(?:geolocation|RTCPeerConnection)\b|\blocation\s*\.\s*(?:reload|assign|replace)\s*\(")


class LandscapeHttpTests(support.WorkspaceCase):
    def setUp(self) -> None:
        super().setUp()
        with self.connect() as con:
            support.add_primary(con)
            con.commit()
        ryd.Handler.db_path = self.db
        ryd.Handler.allow_remote_preview = False
        self.server = ryd.ThreadingHTTPServer(("127.0.0.1", 0), ryd.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = int(self.server.server_address[1])

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        super().tearDown()

    request = support.HttpTests.request

    def test_landscape_route_selects_person_and_retains_private_response_headers(self) -> None:
        with self.connect() as con:
            first = con.execute("SELECT id FROM person").fetchone()[0]
            second = support.add_primary(con, name="Second synthetic person")
            add_listing(con, first, add_broker(con, "NA", "First synthetic broker"))
            add_listing(con, second, add_broker(con, "EU", "Second synthetic broker"), "gone")
            con.commit()
        status, headers, body = self.request("GET", f"/landscape?p={second}")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(headers["referrer-policy"], "no-referrer")
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertNotIn("refresh", headers)
        page = Page(body.decode("utf-8"))
        self.assertEqual(page.payload()["current"], counts(EU=(0, 1)))
        self.assertEqual(page.payload()["history"][-1]["counts"], counts(EU=(0, 1)))
        hrefs = {node.attrs.get("href") for node in page.root.descendants("a")}
        self.assertIn(f"/?p={second}", hrefs)
        self.assertIn(f"/landscape?p={first}", hrefs)
        _, _, dashboard = self.request("GET", f"/?p={second}")
        self.assertIn(f"/landscape?p={second}", {node.attrs.get("href") for node in Page(dashboard.decode("utf-8")).root.descendants("a")})
        _, _, missing = self.request("GET", "/landscape?p=999999")
        self.assertEqual(Page(missing.decode("utf-8")).payload(), {"current": counts(), "history": []})


if __name__ == "__main__":
    unittest.main()
