# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Nick Newsom (@k7cfo) — https://github.com/k7cfo/remove-your-data
"""Synthetic-data tests for the chat-first report/recap/PNG card. Never contacts a broker."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
SPEC = importlib.util.spec_from_file_location("ryd", REPO / "scripts" / "ryd.py")
ryd = importlib.util.module_from_spec(SPEC)
sys.modules["ryd"] = ryd
SPEC.loader.exec_module(ryd)
import ryd_report as rr  # noqa: E402

try:
    import PIL  # noqa: F401
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

PII_STRINGS = ("Jane Q. Public", "Alex", "100 Demo Street", "demo@example.com", "alex.demo",
               "demo-not-real", "optout_demo_1", "wp_demo", "https://", "http://")


def png_info(data: bytes) -> tuple[int, int, bytes]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        n, tag = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        crc = struct.unpack(">I", data[pos + 8 + n:pos + 12 + n])[0]
        assert crc == zlib.crc32(tag + body) & 0xFFFFFFFF, f"bad crc {tag}"
        if tag == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    return w, h, zlib.decompress(idat)


class CardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name) / "ws"
        db = ryd.init_workspace(self.ws)
        with ryd.connect(db, readonly=False) as con:
            ryd.seed_demo(con)
            con.commit()
        self.db = db
        with ryd.connect(db, readonly=True) as con:
            self.report = ryd.load_report(con, None)
        self.now = datetime.now(timezone.utc)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ryd.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_model_rolls_up_worst_status_first(self) -> None:
        m = rr.card_model(self.report, now=self.now)
        order = [v["status"] for v in m["vendors"]]
        self.assertEqual(order, sorted(order, key=rr.ROLLUP_ORDER.index))
        self.assertEqual(m["vendors"][0]["status"], "blocked")
        self.assertEqual(m["total"], sum(m["counts"].values()))
        self.assertEqual(m["who"], "You")

    def test_default_outputs_contain_no_pii_or_urls(self) -> None:
        m = rr.card_model(self.report, now=self.now)
        blobs = [rr.render_md(m), rr.render_text(m), rr.render_json(m), rr.render_recap(self.report, m)]
        for blob in blobs:
            for needle in PII_STRINGS:
                self.assertNotIn(needle, blob, needle)

    def test_names_modes(self) -> None:
        self.assertEqual(rr.card_model(self.report, names="initials")["who"], "JP")
        self.assertEqual(rr.card_model(self.report, names="none")["who"], "Report")

    def test_untrusted_vendor_name_cannot_break_markdown(self) -> None:
        self.report["listings"][0]["broker"] = "Evil | **x** [a](http://e) `rm`\n# h"
        md = rr.render_md(rr.card_model(self.report, now=self.now))
        row = next(l for l in md.splitlines() if "Evil" in l)
        self.assertEqual(row.count("|"), 5)
        self.assertNotIn("http", md)

    def test_overflow_rows_are_summarised(self) -> None:
        base = self.report["listings"][0]
        self.report["listings"] = [dict(base, id=100 + i, broker=f"Vendor {i:02d}") for i in range(20)]
        m = rr.card_model(self.report, now=self.now)
        md = rr.render_md(m)
        self.assertIn("+8 more vendors", md)
        self.assertLessEqual(len(md.splitlines()), 4 + rr.MAX_ROWS + 6)

    def test_empty_ledger(self) -> None:
        empty = Path(self.tmp.name) / "empty"
        db = ryd.init_workspace(empty)
        report = ryd.report_from_db(db)
        m = rr.card_model(report, now=self.now)
        self.assertIn("No listings recorded yet", rr.render_md(m))
        self.assertIn("start intake question 1", rr.render_recap(report, m))
        png, _ = rr.render_png(m, backend="stdlib")
        png_info(png)

    def test_stdlib_png_is_valid_and_not_blank(self) -> None:
        m = rr.card_model(self.report, now=self.now)
        png, used = rr.render_png(m, backend="stdlib")
        self.assertEqual(used, "stdlib")
        w, h, raw = png_info(png)
        self.assertEqual(w, 960)
        self.assertEqual(len(raw), h * (1 + w * 3))
        px = {raw[i:i + 3] for i in range(1, len(raw), 997)}
        self.assertGreater(len(px), 4)
        self.assertLess(len(png), 200_000)

    @unittest.skipUnless(HAVE_PIL, "Pillow not installed")
    def test_pillow_png_is_valid(self) -> None:
        m = rr.card_model(self.report, now=self.now)
        for theme in ("light", "dark"):
            png, used = rr.render_png(m, theme=theme, backend="pillow")
            self.assertEqual(used, "pillow")
            w, h, _ = png_info(png)
            self.assertEqual(w, 960)

    def test_auto_backend_falls_back_without_pillow(self) -> None:
        m = rr.card_model(self.report, now=self.now)
        with mock.patch.dict(os.environ, {"RYD_NO_PIL": "1"}):
            _, used = rr.render_png(m)
        self.assertEqual(used, "stdlib")
        with mock.patch.dict(sys.modules, {"PIL": None}):
            _, used = rr.render_png(m)
        self.assertEqual(used, "stdlib")

    def test_digest_changes_only_when_ledger_changes(self) -> None:
        d0 = rr.ledger_digest(self.report)
        self.assertEqual(d0, rr.ledger_digest(self.report))
        with ryd.connect(self.db, readonly=False) as con:
            con.execute("UPDATE listing SET status='gone' WHERE status='pending_verify'")
            con.commit()
            report2 = ryd.load_report(con, None)
        self.assertNotEqual(d0, rr.ledger_digest(report2))

    def test_recap_has_rules_and_is_short(self) -> None:
        m = rr.card_model(self.report, now=self.now)
        text = rr.render_recap(self.report, m, now=self.now)
        self.assertIn("not recorded", text)
        self.assertIn("RULES", text)
        self.assertLessEqual(len(text.splitlines()), 30)

    def test_cli_image_md_text_json_recap(self) -> None:
        ws = str(self.ws)
        rc, out, err = self.run_cli("report", "--workspace", ws, "--image", "--backend", "stdlib")
        self.assertEqual(rc, 0)
        path = Path(out.strip())
        self.assertTrue(path.exists())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        png_info(path.read_bytes())
        rc, out, _ = self.run_cli("report", "--workspace", ws)
        self.assertIn("| Vendor | Status |", out)
        rc, out, _ = self.run_cli("report", "--workspace", ws, "--json")
        self.assertEqual(json.loads(out)["schema_version"], 1)
        rc, out, _ = self.run_cli("report", "--workspace", ws, "--text", "--names", "none")
        self.assertTrue(out.isascii())
        rc, out, _ = self.run_cli("recap", "--workspace", ws)
        self.assertTrue(out.startswith("RYD RECAP"))

    def test_cli_missing_workspace_is_clean_error(self) -> None:
        rc, _, err = self.run_cli("recap", "--workspace", str(Path(self.tmp.name) / "nope"))
        self.assertEqual(rc, 1)
        self.assertIn("missing", err)

    def test_recap_does_not_write(self) -> None:
        before = self.db.stat().st_mtime_ns
        wal = Path(str(self.db) + "-wal")
        wal_before = wal.stat().st_size if wal.exists() else 0
        self.run_cli("recap", "--workspace", str(self.ws))
        self.run_cli("report", "--workspace", str(self.ws))
        self.assertEqual(before, self.db.stat().st_mtime_ns)
        self.assertEqual(wal_before, wal.stat().st_size if wal.exists() else 0)


if __name__ == "__main__":
    unittest.main()
