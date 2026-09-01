from __future__ import annotations

import argparse
import contextlib
import csv
import http.client
import importlib.util
import io
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlencode


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ryd", REPO / "scripts" / "ryd.py")
assert SPEC and SPEC.loader
ryd = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ryd
SPEC.loader.exec_module(ryd)


def add_primary(
    con: sqlite3.Connection,
    *,
    name: str = "Test Person",
    intake_complete: int = 1,
    drop_filed: int = 0,
) -> int:
    con.execute(
        """
        INSERT INTO person (
          legal_name, residency_country, residency_region, timezone,
          relationship, consent_basis, active, drop_filed, intake_complete,
          created_at_utc
        ) VALUES (?, 'US', 'CA', 'America/Los_Angeles', 'self', 'self', 1, ?, ?, ?)
        """,
        (name, drop_filed, intake_complete, ryd.utc_iso()),
    )
    pid = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
    ryd.add_identifier(con, pid, "name", name)
    return pid


class WorkspaceCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ryd-test-")
        self.workspace = Path(self.tmp.name) / "workspace"
        self.db = ryd.init_workspace(self.workspace)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def connect(self, readonly: bool = False) -> sqlite3.Connection:
        return ryd.connect(self.db, readonly=readonly)


class UnitTests(unittest.TestCase):
    def test_cadence_aliases_and_bounds(self) -> None:
        for raw, expected in (("daily", 24), ("7d", 168), ("24h", 24), ("8760", 8760)):
            with self.subTest(raw=raw):
                self.assertEqual(ryd.parse_cadence(raw), expected)
        for raw in ("0", "0h", "0d", "8761h", "366d", "-1", "nonsense"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    ryd.parse_cadence(raw)

    def test_identifier_normalization(self) -> None:
        self.assertEqual(ryd.normalize_ident("phone", "(916) 555-0142"), "9165550142")
        self.assertEqual(ryd.normalize_ident("email", " A@Example.COM "), "a@example.com")
        self.assertEqual(ryd.normalize_ident("keep_host", "https://www.LinkedIn.com/in/test"), "linkedin.com")

    def test_safe_http_urls(self) -> None:
        for value in ("https://example.com/a", "HTTP://example.com"):
            self.assertTrue(ryd.safe_http_url(value))
        for value in ("javascript:alert(1)", "data:text/html,x", "file:///tmp/x", "httpjavascript://x", "https://"):
            self.assertFalse(ryd.safe_http_url(value))

    def test_scan_pack_excludes_paused_keep_and_dead_host(self) -> None:
        rows = [
            {"kind": "name", "value": "Jane Public", "scan": 1},
            {"kind": "phone", "value": "916-555-0142", "scan": 0},
            {"kind": "keep_host", "value": "linkedin.com", "scan": 0},
        ]
        pack = ryd.scan_pack(rows)
        self.assertIn('"Jane Public" site:spokeo.com', pack)
        self.assertFalse(any("linkedin.com" in q for q in pack))
        self.assertFalse(any("opendatausa.com" in q for q in pack))
        self.assertFalse(any("9165550142" in q for q in pack))

    def test_unsafe_listing_url_is_not_clickable(self) -> None:
        html = ryd.listing_cards(
            [{"status": "found", "broker": "Example", "url": "javascript:alert(1)", "pii_shown": None, "request_id": None}]
        )
        self.assertNotIn('href="javascript:', html)
        self.assertIn("javascript:alert(1)", html)


class WorkspaceTests(WorkspaceCase):
    def test_init_is_idempotent_private_and_complete(self) -> None:
        self.assertEqual(stat.S_IMODE(self.workspace.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.db.stat().st_mode), 0o600)
        ryd.init_workspace(self.workspace)
        with self.connect() as con:
            names = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
        self.assertTrue({"person", "identifier", "listing", "clock", "v_evidence_chronology"} <= names)

    def test_workspace_inside_clone_is_refused(self) -> None:
        target = REPO / "privacy-takedown-test"
        with self.assertRaisesRegex(ValueError, "outside this git clone"):
            ryd.init_workspace(target)
        self.assertFalse(target.exists())

    def test_real_workspace_cannot_preview_off_loopback(self) -> None:
        with mock.patch.dict(os.environ, {"RYD_PREVIEW": "1"}, clear=False):
            with self.assertRaises(SystemExit) as raised:
                ryd.serve(self.db, "0.0.0.0", 0, allow_preview=True)
        self.assertEqual(raised.exception.code, 2)

    def test_child_unconfirmed_consent_is_not_fabricated(self) -> None:
        with self.connect() as con:
            add_primary(con)
            child = ryd.add_family_member(
                con,
                {"legal_name": "Adult Child", "relationship": "child", "consent_basis": "unconfirmed"},
            )
            con.commit()
            row = con.execute("SELECT consent_basis FROM person WHERE id = ?", (child,)).fetchone()
        self.assertEqual(row[0], "unconfirmed")

    def test_pack_refuses_incomplete_primary(self) -> None:
        with self.connect() as con:
            add_primary(con, intake_complete=0)
            con.commit()
        args = argparse.Namespace(workspace=self.workspace, person_id=None)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = ryd.cmd_pack(args)
        self.assertEqual(result, 1)
        self.assertIn("primary intake is incomplete", err.getvalue())

    def test_pack_skips_unconfirmed_family(self) -> None:
        with self.connect() as con:
            add_primary(con)
            ryd.add_family_member(
                con,
                {"legal_name": "No Consent", "relationship": "spouse", "consent_basis": "unconfirmed"},
            )
            con.commit()
        args = argparse.Namespace(workspace=self.workspace, person_id=None)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = ryd.cmd_pack(args)
        self.assertEqual(result, 0)
        self.assertNotIn('"No Consent"', out.getvalue())
        self.assertIn("unconfirmed consent", err.getvalue())

    def test_family_intake_requires_consent_and_unique_email(self) -> None:
        with self.connect() as con:
            add_primary(con)
            family = ryd.add_family_member(
                con,
                {"legal_name": "Authorized Family", "relationship": "spouse", "consent_basis": "authorized_agent"},
            )
            before = con.execute(
                "SELECT intake_complete FROM person WHERE id = ?", (family,)
            ).fetchone()[0]
            ryd.add_identifier(con, family, "email", "family@example.com")
            after = con.execute(
                "SELECT intake_complete FROM person WHERE id = ?", (family,)
            ).fetchone()[0]
            con.commit()
        self.assertEqual(before, 0)
        self.assertEqual(after, 1)

    def test_drop_status_is_per_person(self) -> None:
        with self.connect() as con:
            primary = add_primary(con, drop_filed=1)
            child = ryd.add_family_member(
                con,
                {"legal_name": "Child", "relationship": "child", "consent_basis": "parent_of_minor"},
            )
            con.execute("INSERT INTO config (key, value) VALUES ('drop_filed', '1')")
            con.commit()
            self.assertTrue(ryd.load_report(con, primary)["drop_filed"])
            self.assertFalse(ryd.load_report(con, child)["drop_filed"])

    def test_evidence_csv_is_complete_ordered_and_formula_safe(self) -> None:
        with self.connect() as con:
            first = add_primary(con)
            second = ryd.add_family_member(
                con,
                {"legal_name": "Second Person", "relationship": "spouse", "consent_basis": "authorized_agent"},
            )
            for index in range(205):
                pid = first if index % 2 == 0 else second
                con.execute(
                    """
                    INSERT INTO action_log (
                      person_id, actor, action, result, occurred_at_utc, occurred_at_local
                    ) VALUES (?, 'agent', ?, ?, ?, ?)
                    """,
                    (pid, f"action-{index:03d}", "=HYPERLINK(\"bad\")" if index == 0 else "ok", f"2026-01-01T00:{index // 60:02d}:{index % 60:02d}Z", "local"),
                )
            con.commit()
            rows = list(csv.DictReader(io.StringIO(ryd.render_evidence_csv(con))))
        self.assertEqual(len(rows), 205)
        self.assertEqual({row["person"] for row in rows}, {"Test Person", "Second Person"})
        self.assertTrue(rows[0]["result"].startswith("'="))
        self.assertEqual(rows[0]["action"], "action-000")

    def test_exports_are_private(self) -> None:
        with self.connect() as con:
            add_primary(con)
            con.commit()
        old_umask = os.umask(0o022)
        try:
            self.assertEqual(ryd.cmd_export(argparse.Namespace(workspace=self.workspace, out=None)), 0)
            self.assertEqual(ryd.cmd_export_csv(argparse.Namespace(workspace=self.workspace, out=None)), 0)
        finally:
            os.umask(old_umask)
        for path in (self.workspace / "exports" / "report.html", self.workspace / "exports" / "evidence-log.csv"):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


class HttpTests(WorkspaceCase):
    def setUp(self) -> None:
        super().setUp()
        with self.connect() as con:
            add_primary(con)
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

    def request(self, method: str, path: str, body: str | None = None, headers: dict[str, str] | None = None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        payload = response.read()
        result = response.status, {k.lower(): v for k, v in response.getheaders()}, payload
        conn.close()
        return result

    def test_routes_and_security_headers(self) -> None:
        for path in ("/", "/roster", "/settings", "/export.csv", "/health"):
            with self.subTest(path=path):
                status, headers, _ = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertEqual(headers["cache-control"], "no-store")
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertEqual(headers["referrer-policy"], "no-referrer")
        _, headers, _ = self.request("GET", "/")
        self.assertIn("frame-ancestors 'none'", headers["content-security-policy"])

    def test_foreign_origin_post_is_refused(self) -> None:
        body = urlencode({"cadence_hours": "24", "anonymity_mode": "dedicated", "timezone": "UTC", "refresh_seconds": "30"})
        status, _, payload = self.request(
            "POST",
            "/settings",
            body,
            {"Content-Type": "application/x-www-form-urlencoded", "Origin": "https://evil.example"},
        )
        self.assertEqual(status, 403)
        self.assertIn(b"cross-origin", payload)

    def test_same_origin_post_succeeds(self) -> None:
        host = f"127.0.0.1:{self.port}"
        body = urlencode({"cadence_hours": "24", "anonymity_mode": "dedicated", "timezone": "UTC", "refresh_seconds": "30"})
        status, headers, _ = self.request(
            "POST",
            "/settings",
            body,
            {"Host": host, "Origin": f"http://{host}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 303)
        self.assertEqual(headers["location"], "/settings?ok=Saved.")

    def test_dns_rebinding_host_is_refused(self) -> None:
        status, _, payload = self.request("GET", "/", headers={"Host": "evil.example"})
        self.assertEqual(status, 403)
        self.assertIn(b"untrusted Host", payload)


class CliSmokeTests(unittest.TestCase):
    def test_cli_init_settings_and_exports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ryd-cli-") as tmp:
            workspace = Path(tmp) / "workspace"
            script = REPO / "scripts" / "ryd.py"
            init = subprocess.run(
                [sys.executable, str(script), "init", "--workspace", str(workspace)],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            show = subprocess.run(
                [sys.executable, str(script), "settings", "--workspace", str(workspace), "--show"],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(show.returncode, 0, show.stderr)
            self.assertIn("cadence_hours=168", show.stdout)

    def test_demo_flag_cannot_expose_existing_real_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ryd-cli-") as tmp:
            workspace = Path(tmp) / "workspace"
            db = ryd.init_workspace(workspace)
            with ryd.connect(db, readonly=False) as con:
                add_primary(con)
                con.commit()
            env = dict(os.environ)
            env["RYD_PREVIEW"] = "1"
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO / "scripts" / "ryd.py"),
                    "serve",
                    "--demo",
                    "--workspace",
                    str(workspace),
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "0",
                ],
                cwd=REPO,
                env=env,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("not synthetic demo data", result.stderr)


if __name__ == "__main__":
    unittest.main()
