# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Nick Newsom (@k7cfo) — https://github.com/k7cfo/remove-your-data
"""US state law packs: validation, selection, clocks, rendering and ledger rules."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


laws = _load("ryd_laws")
ryd = sys.modules.get("ryd") or _load("ryd")

PACKS = laws.load_packs()
RECEIVED = date(2026, 11, 2)  # a Monday
TODAY = date(2026, 10, 29)

# code: (response, extension, appeal response, appeal extension, deletion scope,
#        agent for opt_out, agent for delete)
EXPECTED = {
    "CA": (45, 45, None, None, "collected_from_consumer", True, True),
    "CO": (45, 45, 45, 60, "all_personal_data", True, False),
    "CT": (45, 45, 60, None, "all_personal_data", True, False),
    "DE": (45, 45, 60, None, "all_personal_data", True, False),
    "FL": (45, 15, 60, None, "all_personal_data", False, False),
    "IN": (45, 45, 60, None, "all_personal_data", False, False),
    "IA": (90, 45, 60, None, "provided_by_consumer", False, False),
    "KY": (45, 45, 60, None, "all_personal_data", False, False),
    "MD": (45, 45, 60, None, "all_personal_data", True, False),
    "MN": (45, 45, 45, 60, "all_personal_data", True, False),
    "MT": (45, 45, 60, None, "all_personal_data", True, False),
    "NE": (45, 45, 60, None, "all_personal_data", True, False),
    "NH": (45, 45, 60, None, "all_personal_data", True, False),
    "NJ": (45, 45, 45, None, "all_personal_data", True, False),
    "OR": (45, 45, 45, None, "all_personal_data", True, False),
    "RI": (45, 45, 60, None, "all_personal_data", True, False),
    "TN": (45, 45, 60, None, "all_personal_data", False, False),
    "TX": (45, 45, 60, None, "all_personal_data", True, False),
    "UT": (45, 45, None, None, "provided_by_consumer", None, None),
    "VA": (45, 45, 60, None, "all_personal_data", None, None),
}
EFFECTIVE = {
    "CA": "2020-01-01", "CO": "2023-07-01", "CT": "2023-07-01", "DE": "2025-01-01",
    "FL": "2024-07-01", "IN": "2026-01-01", "IA": "2025-01-01", "KY": "2026-01-01",
    "MD": "2025-10-01", "MN": "2025-07-31", "MT": "2024-10-01", "NE": "2025-01-01",
    "NH": "2025-01-01", "NJ": "2025-01-15", "OR": "2024-07-01", "RI": "2026-01-01",
    "TN": "2025-07-01", "TX": "2024-07-01", "UT": "2023-12-31", "VA": "2023-01-01",
}


def pack(code: str) -> dict:
    return PACKS[f"us-{code.lower()}"]


def select(code: str, **kw):
    args = {"on": TODAY, "today": TODAY, "attested": True}
    args.update(kw)
    return laws.select_pack(PACKS, code, **args)


class PackDataTests(unittest.TestCase):
    def test_every_pack_validates(self) -> None:
        results = laws.validate_dir()
        self.assertEqual({k: v for k, v in results.items() if v}, {})
        self.assertEqual(len(results), 21)

    def test_schema_documents_the_validator_keys(self) -> None:
        schema = json.loads((REPO / "laws" / "schema.json").read_text(encoding="utf-8"))
        self.assertEqual(tuple(schema["required"]), laws.TOP_KEYS)

    def test_regions_cover_fifty_states_and_dc(self) -> None:
        self.assertEqual(len(laws.US_REGIONS), 51)
        self.assertIn("DC", laws.US_REGIONS)

    def test_matrix_of_twenty_states(self) -> None:
        states = sorted(p["jurisdiction"]["region"] for p in PACKS.values() if p["pack_id"] != "us-universal")
        self.assertEqual(states, sorted(EXPECTED))

    def test_effective_dates(self) -> None:
        for code, eff in EFFECTIVE.items():
            with self.subTest(code=code):
                self.assertEqual(pack(code)["law"]["effective_date"], eff)

    def test_sources_hashed_and_checked(self) -> None:
        for p in PACKS.values():
            for s in p["sources"]:
                with self.subTest(pack=p["pack_id"], source=s["id"]):
                    self.assertEqual(s["checked_on"], "2026-10-29")
                    self.assertRegex(s["sha256"], r"^[0-9a-f]{64}$")
                    self.assertTrue(s["url"].startswith("https://"))

    def test_no_numeric_appeal_filing_window(self) -> None:
        for p in PACKS.values():
            ap = p["clocks"]["appeal"]
            with self.subTest(pack=p["pack_id"]):
                self.assertNotIsInstance(ap.get("consumer_filing_window"), int)
                if ap["available"]:
                    self.assertIn("reasonable", ap["consumer_filing_window"])


class ClockTests(unittest.TestCase):
    def test_response_extension_and_appeal_per_state(self) -> None:
        for code, (resp, ext, appeal, appeal_ext, _scope, _a, _d) in EXPECTED.items():
            p = pack(code)
            with self.subTest(code=code):
                clocks = {c["name"]: c for c in laws.compute_clocks(p, RECEIVED, ["delete"])}
                self.assertEqual(clocks["response"]["due"], date.fromordinal(RECEIVED.toordinal() + resp).isoformat())
                ext_rows = {c["name"]: c for c in laws.compute_clocks(p, RECEIVED, ["delete"], extended=True)}
                self.assertEqual(ext_rows["extended_response"]["due"],
                                 date.fromordinal(RECEIVED.toordinal() + resp + ext).isoformat())
                self.assertEqual(p["clocks"]["extension"]["days"], ext)
                if appeal is None:
                    with self.assertRaises(laws.LawError):
                        laws.appeal_clock(p, RECEIVED)
                else:
                    self.assertEqual(laws.appeal_clock(p, RECEIVED)["due"],
                                     date.fromordinal(RECEIVED.toordinal() + appeal).isoformat())
                if appeal_ext is None:
                    if appeal is not None:
                        with self.assertRaises(laws.LawError):
                            laws.appeal_clock(p, RECEIVED, extended=True)
                else:
                    self.assertEqual(laws.appeal_clock(p, RECEIVED, extended=True)["due"],
                                     date.fromordinal(RECEIVED.toordinal() + appeal + appeal_ext).isoformat())

    def test_extension_notice_must_fall_in_initial_period(self) -> None:
        for code, (resp, *_rest) in EXPECTED.items():
            p = pack(code)
            last = date.fromordinal(RECEIVED.toordinal() + resp)
            with self.subTest(code=code):
                self.assertTrue(laws.extension_allowed(p, RECEIVED, last))
                self.assertFalse(laws.extension_allowed(p, RECEIVED, date.fromordinal(last.toordinal() + 1)))

    def test_california_business_day_clocks(self) -> None:
        p = pack("CA")
        start = date(2026, 11, 20)  # Friday before Thanksgiving week
        rows = {c["name"]: c for c in laws.compute_clocks(p, start, ["delete", "opt_out"])}
        self.assertEqual(rows["acknowledgement"]["due"], "2026-12-07")
        self.assertEqual(rows["acknowledgement"]["day_type"], "business")
        self.assertEqual(rows["opt_out"]["due"], "2026-12-14")
        self.assertEqual(rows["response"]["due"], "2027-01-04")
        only_opt = {c["name"] for c in laws.compute_clocks(p, start, ["opt_out"])}
        self.assertEqual(only_opt, {"opt_out"})

    def test_other_states_count_opt_out_in_the_response_clock(self) -> None:
        rows = laws.compute_clocks(pack("CO"), RECEIVED, ["opt_out"])
        self.assertEqual([r["name"] for r in rows], ["response"])

    def test_federal_holidays_observed(self) -> None:
        h2027 = laws.us_federal_holidays(2027)
        self.assertIn(date(2027, 6, 18), h2027)    # Juneteenth on Saturday
        self.assertIn(date(2027, 12, 24), h2027)   # Christmas on Saturday
        self.assertIn(date(2027, 12, 31), h2027)   # 2028-01-01 is a Saturday
        self.assertIn(date(2026, 11, 26), laws.us_federal_holidays(2026))
        self.assertFalse(laws.is_business_day(date(2026, 11, 28)))
        self.assertEqual(laws.add_days(date(2026, 12, 31), 1, "business"), date(2027, 1, 4))
        with self.assertRaises(laws.LawError):
            laws.add_days(RECEIVED, 1, "fortnight")


class SelectionTests(unittest.TestCase):
    def test_state_pack_when_attested_and_in_effect(self) -> None:
        sel = select("CO")
        self.assertFalse(sel.universal)
        self.assertEqual(sel.reason, "state_pack")
        self.assertEqual(sel.pack_ref, "us-co@2026.10.29")

    def test_fallbacks(self) -> None:
        cases = {
            "no_pack": select("NY"),
            "no_attestation": select("CO", attested=False),
            "not_yet_effective": select("KY", on=date(2025, 12, 31)),
            "stale": select("CO", today=date(2027, 4, 30)),
            "narrow_law": select("FL"),
            "requested_universal": select("CO", force_universal=True),
        }
        for reason, sel in cases.items():
            with self.subTest(reason=reason):
                self.assertTrue(sel.universal)
                self.assertEqual(sel.reason, reason)
                self.assertEqual(sel.pack["pack_id"], "us-universal")

    def test_review_date_itself_is_not_stale(self) -> None:
        self.assertFalse(select("CO", today=date(2027, 4, 29)).universal)

    def test_superseded_follows_replacement_or_falls_back(self) -> None:
        packs = copy.deepcopy(PACKS)
        old = packs["us-co"]
        old["status"] = "superseded"
        old["superseded_by"] = "us-co-2027"
        sel = laws.select_pack(packs, "CO", on=TODAY, today=TODAY, attested=True)
        self.assertTrue(sel.universal)
        self.assertEqual(sel.reason, "superseded")
        new = copy.deepcopy(PACKS["us-co"])
        new["pack_id"] = "us-co-2027"
        new["pack_version"] = "2026.11.01"
        new["supersedes"] = "us-co@2026.10.29"
        new["changelog"].append({"version": "2026.11.01", "date": "2026-11-01", "change": "test"})
        self.assertEqual(laws.validate_pack(new, "us-co-2027.json"), [])
        packs["us-co-2027"] = new
        sel = laws.select_pack(packs, "CO", on=TODAY, today=TODAY, attested=True)
        self.assertFalse(sel.universal)
        self.assertEqual(sel.pack_ref, "us-co-2027@2026.11.01")

    def test_unverified_or_invalid_pack_falls_back(self) -> None:
        packs = copy.deepcopy(PACKS)
        packs["us-tx"]["status"] = "unverified"
        self.assertEqual(laws.select_pack(packs, "TX", on=TODAY, today=TODAY, attested=True).reason, "unverified")
        packs["us-tx"]["status"] = "current"
        packs["us-tx"]["clocks"]["response"]["day_type"] = "weeks"
        self.assertEqual(laws.select_pack(packs, "TX", on=TODAY, today=TODAY, attested=True).reason, "invalid_pack")

    def test_florida_needs_coverage_assertion(self) -> None:
        sel = select("FL", controller_covered=True)
        self.assertFalse(sel.universal)
        self.assertEqual(sel.pack["clocks"]["extension"]["days"], 15)

    def test_california_routes_to_drop_first(self) -> None:
        sel = select("CA")
        self.assertTrue(any("DROP" in w for w in sel.warnings))

    def test_non_us_region_rejected(self) -> None:
        with self.assertRaises(laws.LawError):
            select("ON")


class RenderTests(unittest.TestCase):
    def render(self, code: str, rights=("delete", "opt_out"), sender="self", **kw):
        return laws.render_request(select(code, **kw), controller="Example Data Co",
                                   name="Demo Person", rights=list(rights), sender=sender)[1]

    def test_universal_makes_no_statutory_claim(self) -> None:
        for region in laws.US_REGIONS:
            sel = laws.select_pack(PACKS, region, on=TODAY, today=TODAY, attested=False)
            with self.subTest(region=region):
                self.assertTrue(sel.universal)
                text = laws.render_request(sel, controller="Example Data Co", name="Demo Person",
                                           rights=["delete", "opt_out"], sender="self")[1]
                self.assertIn("voluntary request", text)
                self.assertNotRegex(text, r"\d+ (business )?days")
                self.assertNotIn("subject to", text)
                self.assertNotIn("$", text)

    def test_state_wording_is_conditional(self) -> None:
        for code in EXPECTED:
            kw = {"controller_covered": True} if code == "FL" else {}
            with self.subTest(code=code):
                text = self.render(code, **kw)
                self.assertIn("To the extent your organization is subject to", text)
                self.assertIn(pack(code)["law"]["name"], text)
                self.assertNotIn("$", text)
                self.assertNotIn("\n\n\n", text)

    def test_appeal_sentence_only_where_an_appeal_exists(self) -> None:
        self.assertNotIn("how to appeal", self.render("UT"))
        self.assertNotIn("how to appeal", self.render("CA"))
        self.assertIn("how to appeal", self.render("CO"))

    def test_narrow_deletion_scope_adds_voluntary_ask(self) -> None:
        for code in ("IA", "UT"):
            with self.subTest(code=code):
                self.assertIn("may cover only personal data I provided to you", self.render(code))
        self.assertIn("you collected from me", self.render("CA"))
        self.assertNotIn("may cover only", self.render("CO"))
        self.assertNotIn("may cover only", self.render("IA", rights=("opt_out",)))
        self.assertIn("minimal record", self.render("OR"))

    def test_california_text_names_business_day_clocks(self) -> None:
        text = self.render("CA")
        self.assertIn("10 business days", text)
        self.assertIn("15 business days", text)

    def test_authorized_agent_rules(self) -> None:
        for code, (*_r, agent_opt, agent_delete) in EXPECTED.items():
            kw = {"controller_covered": True} if code == "FL" else {}
            with self.subTest(code=code):
                if agent_delete is False:
                    with self.assertRaises(laws.LawError):
                        self.render(code, rights=("delete",), sender="agent", **kw)
                else:
                    self.assertIn("authorized agent", self.render(code, rights=("delete",), sender="agent", **kw))
                if agent_opt is False:
                    with self.assertRaises(laws.LawError):
                        self.render(code, rights=("opt_out",), sender="agent", **kw)
                else:
                    self.render(code, rights=("opt_out",), sender="agent", **kw)
        blocked, unknown = laws.agent_check(pack("UT"), ["delete"], "agent")
        self.assertEqual((blocked, unknown), ([], ["delete"]))
        self.assertEqual(laws.agent_check(pack("CO"), ["delete"], "self"), ([], []))

    def test_appeal_letter(self) -> None:
        _tid, text = laws.render_appeal(pack("MN"), "MN", controller="Example Data Co", name="Demo Person",
                                        received_on="2026-11-02", sender="self")
        self.assertIn("within 45 days", text)
        self.assertIn("60 more days", text)
        with self.assertRaises(laws.LawError):
            laws.render_appeal(pack("UT"), "UT", controller="X", name="Y", received_on="2026-11-02", sender="self")

    def test_parse_rights(self) -> None:
        self.assertEqual(laws.parse_rights(None), ["delete", "opt_out"])
        self.assertEqual(laws.parse_rights("opt-out, delete,delete"), ["opt_out", "delete"])
        with self.assertRaises(laws.LawError):
            laws.parse_rights("erase")


class ValidatorTests(unittest.TestCase):
    def errors(self, mutate) -> list[str]:
        p = copy.deepcopy(pack("CO"))
        mutate(p)
        return laws.validate_pack(p, "us-co.json")

    def test_rejects_bad_packs(self) -> None:
        def numeric_window(p): p["clocks"]["appeal"]["consumer_filing_window"] = 30
        def bad_hash(p): p["sources"][0]["sha256"] = "abc"
        def unknown_source(p): p["clocks"]["response"]["source"] = "nope"
        def day_type(p): p["clocks"]["extension"]["day_type"] = "weeks"
        def no_changelog(p): p["changelog"] = [{"version": "2000.01.01", "date": "2000-01-01", "change": "x"}]
        def http(p): p["sources"][0]["url"] = "http://example.com"
        def agent(p): p["rights"]["delete"]["authorized_agent"] = "yes"
        def review(p): p["review_by"] = p["verified_on"]
        def extra(p): p["surprise"] = 1
        def superseded(p): p["status"] = "superseded"
        for fn in (numeric_window, bad_hash, unknown_source, day_type, no_changelog, http, agent,
                   review, extra, superseded):
            with self.subTest(fn=fn.__name__):
                self.assertTrue(self.errors(fn))
        self.assertTrue(laws.validate_pack(pack("CO"), "us-tx.json"))

    def test_universal_cannot_carry_clocks(self) -> None:
        p = copy.deepcopy(PACKS["us-universal"])
        p["clocks"]["response"] = copy.deepcopy(pack("CO")["clocks"]["response"])
        self.assertTrue(laws.validate_pack(p, "us-universal.json"))

    def test_validate_dir_flags_missing_universal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "us-co.json").write_text(json.dumps(pack("CO")), encoding="utf-8")
            res = laws.validate_dir(Path(tmp))
            self.assertIn("(set)", res)


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ryd-laws-")
        self.workspace = Path(self.tmp.name) / "ws"
        self.db = ryd.init_workspace(self.workspace)
        self.con = ryd.connect(self.db, readonly=False)

    def tearDown(self) -> None:
        self.con.close()
        self.tmp.cleanup()

    def person(self, region="CO", consent="self", intake=1, relationship="self") -> int:
        self.con.execute(
            "INSERT INTO person (legal_name, residency_country, residency_region, relationship,"
            " consent_basis, active, intake_complete, created_at_utc) VALUES (?, 'US', ?, ?, ?, 1, ?, ?)",
            ("Demo Person", region, relationship, consent, intake, ryd.utc_iso()),
        )
        return int(self.con.execute("SELECT last_insert_rowid()").fetchone()[0])

    def request(self, pid, **kw):
        args = {"rights": ["delete", "opt_out"], "today": TODAY, "packs": PACKS}
        args.update(kw)
        return ryd.create_law_request(self.con, pid, "Example Data Co", **args)

    def clocks(self):
        return [dict(r) for r in self.con.execute("SELECT * FROM clock ORDER BY id")]

    def test_attestation_needs_confirmed_consent(self) -> None:
        pid = self.person(consent="unconfirmed", relationship="other")
        with self.assertRaises(ValueError):
            ryd.record_attestation(self.con, pid, "CO")
        with self.assertRaises(ValueError):
            ryd.record_attestation(self.con, self.person(), "ZZ")

    def test_reattest_revokes_previous(self) -> None:
        pid = self.person()
        a1 = ryd.record_attestation(self.con, pid, "CO", "2026-10-01")
        a2 = ryd.record_attestation(self.con, pid, "TX", "2026-10-29")
        self.assertNotEqual(a1, a2)
        self.assertEqual(ryd.current_attestation(self.con, pid)["region"], "TX")

    def test_filing_needs_intake_and_consent(self) -> None:
        pid = self.person(intake=0)
        with self.assertRaises(ValueError):
            self.request(pid)

    def test_no_attestation_records_universal_without_clocks(self) -> None:
        pid = self.person()
        out = self.request(pid, received_on="2026-11-02")
        row = ryd.get_law_request(self.con, out["id"])
        self.assertEqual(row["pack_id"], "us-universal")
        self.assertEqual(row["selection_reason"], "no_attestation")
        self.assertEqual(self.clocks(), [])

    def test_state_request_records_text_pack_and_clocks(self) -> None:
        pid = self.person()
        aid = ryd.record_attestation(self.con, pid, "CO")
        out = self.request(pid, received_on="2026-11-02")
        row = ryd.get_law_request(self.con, out["id"])
        self.assertEqual(row["rendered_text"], out["text"])
        self.assertEqual(row["rendered_sha256"], laws.sha256_text(out["text"]))
        self.assertEqual((row["pack_id"], row["pack_version"], row["attestation_id"]), ("us-co", "2026.10.29", aid))
        self.assertEqual(row["received_on"], "2026-11-02")
        self.assertTrue(json.loads(row["assumptions"]))
        clocks = self.clocks()
        self.assertEqual(len(clocks), 1)
        c = clocks[0]
        self.assertEqual(c["kind"], "legal_response")
        self.assertEqual(c["due_at_utc"], "2026-12-17T23:59:59Z")
        for needle in ("us-co@2026.10.29", f"attestation #{aid}", "receipt 2026-11-02", "calendar"):
            self.assertIn(needle, c["notes"])

    def test_overdue_only_after_due_date(self) -> None:
        pid = self.person()
        ryd.record_attestation(self.con, pid, "CO")
        self.request(pid, received_on="2026-11-02")
        self.con.commit()
        from datetime import datetime, timezone
        from unittest import mock
        with mock.patch.object(ryd, "utcnow", return_value=datetime(2026, 12, 17, 12, tzinfo=timezone.utc)):
            self.assertEqual(ryd.load_report(self.con, pid)["overdue"], [])
        with mock.patch.object(ryd, "utcnow", return_value=datetime(2026, 12, 18, 1, tzinfo=timezone.utc)):
            self.assertEqual(len(ryd.load_report(self.con, pid)["overdue"]), 1)

    def test_no_clock_without_receipt_date(self) -> None:
        pid = self.person()
        ryd.record_attestation(self.con, pid, "CO")
        out = self.request(pid)
        self.assertEqual(self.clocks(), [])
        res = ryd.law_request_event(self.con, out["id"], "received", "2026-11-02", packs=PACKS)
        self.assertEqual([c["name"] for c in res["clocks"]], ["response"])
        with self.assertRaises(ValueError):
            ryd.law_request_event(self.con, out["id"], "received", "2026-11-03", packs=PACKS)

    def test_pack_version_change_blocks_new_clocks(self) -> None:
        pid = self.person()
        ryd.record_attestation(self.con, pid, "CO")
        out = self.request(pid)
        newer = copy.deepcopy(PACKS)
        newer["us-co"]["pack_version"] = "2027.01.01"
        res = ryd.law_request_event(self.con, out["id"], "received", "2026-11-02", packs=newer)
        self.assertIn("re-plan", res["note"])
        self.assertEqual(self.clocks(), [])

    def test_extension_and_late_extension(self) -> None:
        pid = self.person()
        ryd.record_attestation(self.con, pid, "CO")
        out = self.request(pid, received_on="2026-11-02")
        with self.assertRaises(ValueError):
            ryd.law_request_event(self.con, out["id"], "extended", "2026-12-18", packs=PACKS)
        res = ryd.law_request_event(self.con, out["id"], "extended", "2026-12-17", packs=PACKS)
        self.assertEqual(res["clocks"][0]["due"], "2027-01-31")
        rows = self.clocks()
        self.assertEqual([r["status"] for r in rows], ["done", "open"])
        ryd.law_request_event(self.con, out["id"], "closed", "2027-01-10", packs=PACKS)
        self.assertEqual({r["status"] for r in self.clocks()}, {"done"})

    def test_appeal_flow(self) -> None:
        pid = self.person(region="MN")
        ryd.record_attestation(self.con, pid, "MN")
        out = self.request(pid, received_on="2026-11-02")
        appeal = ryd.create_law_appeal(self.con, out["id"], packs=PACKS)
        self.assertIn("appeal your decision", appeal["text"])
        res = ryd.law_request_event(self.con, appeal["id"], "received", "2027-01-04", packs=PACKS)
        self.assertEqual(res["clocks"][0]["due"], "2027-02-18")
        res = ryd.law_request_event(self.con, appeal["id"], "extended", "2027-02-01", packs=PACKS)
        self.assertEqual(res["clocks"][0]["due"], "2027-04-19")

    def test_no_appeal_in_utah_or_for_universal(self) -> None:
        pid = self.person(region="UT")
        ryd.record_attestation(self.con, pid, "UT")
        out = self.request(pid, received_on="2026-11-02")
        with self.assertRaises(ValueError):
            ryd.create_law_appeal(self.con, out["id"], packs=PACKS)
        uni = self.request(pid, force_universal=True, received_on="2026-11-02")
        with self.assertRaises(ValueError):
            ryd.create_law_appeal(self.con, uni["id"], packs=PACKS)

    def test_agent_blocked_rights_refuse_to_render(self) -> None:
        pid = self.person(consent="authorized_agent", relationship="other")
        ryd.record_attestation(self.con, pid, "CO")
        ryd.record_filer(self.con, pid, mode="authorized_agent", filer="friend", relationship="other_adult",
                         consent_basis="subject_consent", consent_on="2026-10-01",
                         consent_note="asked me in writing")
        with self.assertRaises(ValueError):
            self.request(pid, rights=["delete"])
        out = self.request(pid, rights=["opt_out"])
        self.assertIn("authorized agent", out["text"])
        plan = ryd.plan_law_request(self.con, pid, rights=["delete"], today=TODAY, packs=PACKS)
        self.assertEqual(plan["blocked"], ["delete"])

    def test_florida_default_is_universal(self) -> None:
        pid = self.person(region="FL")
        ryd.record_attestation(self.con, pid, "FL")
        self.assertEqual(self.request(pid)["plan"]["reason"], "narrow_law")
        self.assertEqual(self.request(pid, controller_covered=True)["plan"]["reason"], "state_pack")

    def test_cli_plan_request_event_and_recap(self) -> None:
        pid = self.person()
        self.con.commit()
        ws = str(self.workspace)

        def run(*argv):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = ryd.main(list(argv))
            return code, out.getvalue(), err.getvalue()

        self.assertEqual(run("attest-residency", "--workspace", ws, "--person-id", str(pid), "--region", "CO")[0], 2)
        self.assertEqual(run("attest-residency", "--workspace", ws, "--person-id", str(pid), "--region", "CO", "--confirm")[0], 0)
        code, out, _ = run("law-plan", "--workspace", ws, "--person-id", str(pid), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["pack"].split("@")[0], "us-co")
        dest = self.workspace / "exports" / "req.txt"
        code, out, err = run("law-request", "--workspace", ws, "--person-id", str(pid),
                             "--controller", "Example Data Co", "--out", str(dest))
        self.assertEqual(code, 0, err)
        self.assertEqual(dest.stat().st_mode & 0o777, 0o600)
        code, out, _ = run("law-event", "--workspace", ws, "--request-id", "1", "--event", "received",
                           "--date", "2026-11-02")
        self.assertEqual(code, 0)
        self.assertIn("2026-12-17", out)
        code, out, _ = run("recap", "--workspace", ws)
        self.assertEqual(code, 0)
        self.assertIn("Example Data Co", out)
        code, out, _ = run("report", "--workspace", ws, "--json")
        self.assertEqual(code, 0)
        self.assertNotIn("Demo Person", out)
        self.assertEqual(run("law-validate")[0], 0)

    def test_migrate_is_idempotent_with_new_tables(self) -> None:
        self.con.close()
        ryd.init_workspace(self.workspace)
        self.con = ryd.connect(self.db, readonly=False)
        tables = {r[0] for r in self.con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"residency_attestation", "privacy_request", "privacy_request_clock"} <= tables)


class FilingModeTests(unittest.TestCase):
    """Household-inbox filing: a family helper files the person's own request from their inbox."""

    INBOX = "subject.demo@example.com"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ryd-filing-")
        self.workspace = Path(self.tmp.name) / "ws"
        self.db = ryd.init_workspace(self.workspace)
        self.con = ryd.connect(self.db, readonly=False)

    def tearDown(self) -> None:
        self.con.close()
        self.tmp.cleanup()

    def person(self, region="CO", consent="authorized_agent", relationship="spouse", name="Sam Example") -> int:
        self.con.execute(
            "INSERT INTO person (legal_name, residency_country, residency_region, relationship,"
            " consent_basis, active, intake_complete, created_at_utc) VALUES (?, 'US', ?, ?, ?, 1, 1, ?)",
            (name, region, relationship, consent, ryd.utc_iso()),
        )
        pid = int(self.con.execute("SELECT last_insert_rowid()").fetchone()[0])
        ryd.record_attestation(self.con, pid, region)
        return pid

    def household(self, pid, **kw) -> int:
        args = dict(mode="household_inbox", filer="spouse", relationship="spouse_partner",
                    consent_basis="subject_consent", consent_on="2026-10-01",
                    consent_note="asked me in person to handle this", inbox=self.INBOX,
                    inbox_permission=True)
        args.update(kw)
        return ryd.record_filer(self.con, pid, **args)

    def request(self, pid, rights=("delete", "opt_out"), **kw):
        return ryd.create_law_request(self.con, pid, "Example Data Co", rights=list(rights),
                                      today=TODAY, packs=PACKS, **kw)

    def assert_first_person(self, text: str, name: str) -> None:
        for phrase in ("agent", "on their behalf", "on behalf of", "guardian", "helping",
                       "I am sending this request myself"):
            self.assertNotIn(phrase, text)
        self.assertIn(f"Name: {name}", text)
        self.assertIn(f"Reply to: {self.INBOX}", text)

    # consent for adults

    def test_adult_needs_a_consent_record_before_filing(self) -> None:
        pid = self.person()
        with self.assertRaisesRegex(ValueError, "consent record"):
            self.request(pid)
        plan = ryd.plan_law_request(self.con, pid, rights=["delete"], today=TODAY, packs=PACKS)
        self.assertIsNone(plan["filing_mode"])
        self.assertTrue(any("household_inbox" in w for w in plan["warnings"]))

    def test_adult_consent_fields_are_required(self) -> None:
        pid = self.person()
        bad = [
            {"consent_on": None},
            {"consent_note": "  "},
            {"consent_basis": "parent_or_guardian_of_minor"},
            {"inbox_permission": False},
            {"inbox": None},
            {"inbox": "not-an-address"},
            {"relationship": "other_adult"},
            {"relationship": "parent_of_minor"},
            {"mode": "guardian"},
            {"mode": "self"},
            {"filer": ""},
        ]
        for change in bad:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    self.household(pid, **change)
        self.assertIsNone(ryd.current_filer(self.con, pid))

    def test_unconfirmed_roster_person_cannot_get_a_filer(self) -> None:
        pid = self.person()
        self.con.execute("UPDATE person SET consent_basis = 'unconfirmed' WHERE id = ?", (pid,))
        with self.assertRaises(ValueError):
            self.household(pid)

    def test_filing_record_rechecked_against_roster(self) -> None:
        pid = self.person()
        self.household(pid)
        self.con.execute("UPDATE person SET consent_basis = 'parent_of_minor' WHERE id = ?", (pid,))
        with self.assertRaisesRegex(ValueError, "no longer fits"):
            self.request(pid)

    def test_household_inbox_letter_is_first_person_and_recorded(self) -> None:
        pid = self.person()
        fid = self.household(pid)
        out = self.request(pid)
        self.assert_first_person(out["text"], "Sam Example")
        self.assertIn("I am a resident of Colorado", out["text"])
        self.assertIn("To the extent your organization is subject to", out["text"])
        row = ryd.get_law_request(self.con, out["id"])
        self.assertEqual((row["filing_mode"], row["filing_authority_id"], row["inbox"], row["sender"]),
                         ("household_inbox", fid, self.INBOX, "household"))
        self.assertTrue(any("not an authorized-agent filing" in a for a in json.loads(row["assumptions"])))
        auth = ryd.current_filer(self.con, pid)
        self.assertEqual((auth["filer"], auth["relationship"], auth["consent_basis"]),
                         ("spouse", "spouse_partner", "subject_consent"))

    def test_household_inbox_skips_agent_restrictions(self) -> None:
        for code, (*_r, agent_opt, agent_delete) in EXPECTED.items():
            if code == "FL":
                continue
            with self.subTest(code=code):
                pid = self.person(region=code)
                self.household(pid)
                plan = ryd.plan_law_request(self.con, pid, rights=["delete", "opt_out"], today=TODAY, packs=PACKS)
                self.assertEqual(plan["blocked"], [])
                self.assertFalse(any("agent may submit" in w.lower() for w in plan["warnings"]))
                out = self.request(pid)
                self.assert_first_person(out["text"], "Sam Example")

    def test_household_universal_letter_has_no_helper_language(self) -> None:
        pid = self.person(region="NY")
        self.household(pid)
        out = self.request(pid)
        self.assertIn("voluntary request", out["text"])
        self.assert_first_person(out["text"], "Sam Example")

    def test_household_appeal_keeps_first_person(self) -> None:
        pid = self.person(region="MN")
        self.household(pid)
        out = self.request(pid, received_on="2026-11-02")
        appeal = ryd.create_law_appeal(self.con, out["id"], packs=PACKS)
        self.assert_first_person(appeal["text"], "Sam Example")
        self.assertEqual(ryd.get_law_request(self.con, appeal["id"])["filing_mode"], "household_inbox")

    def test_adult_family_member_allowed(self) -> None:
        pid = self.person(relationship="adult child")
        self.household(pid, filer="parent", relationship="adult_family_member")
        self.assert_first_person(self.request(pid)["text"], "Sam Example")

    # minors

    def test_minor_default_is_guardian_letter_with_tip(self) -> None:
        pid = self.person(consent="parent_of_minor", relationship="child", name="Alex Example")
        plan = ryd.plan_law_request(self.con, pid, rights=["delete"], today=TODAY, packs=PACKS)
        self.assertEqual(plan["filing_mode"], "guardian")
        self.assertTrue(any("household_inbox" in w for w in plan["warnings"]))
        self.assertIn("parent or legal guardian", self.request(pid)["text"])

    def test_minor_household_inbox_from_guardian(self) -> None:
        pid = self.person(consent="parent_of_minor", relationship="child", name="Alex Example")
        with self.assertRaises(ValueError):
            self.household(pid, filer="parent", relationship="parent_of_minor")  # wrong consent basis
        with self.assertRaises(ValueError):
            self.household(pid, filer="parent", relationship="parent_of_minor",
                           consent_basis="parent_or_guardian_of_minor", mode="authorized_agent")
        self.household(pid, filer="parent", relationship="parent_of_minor",
                       consent_basis="parent_or_guardian_of_minor", consent_on=None, consent_note=None)
        out = self.request(pid)
        self.assert_first_person(out["text"], "Alex Example")
        plan = out["plan"]
        self.assertEqual(plan["filing_mode"], "household_inbox")
        self.assertFalse(any("household_inbox" in w for w in plan["warnings"]))

    # agent path unchanged

    def test_agent_path_keeps_state_checks(self) -> None:
        pid = self.person()
        self.household(pid, mode="authorized_agent", inbox=None, inbox_permission=False)
        with self.assertRaises(ValueError):
            self.request(pid, rights=["delete"])
        text = self.request(pid, rights=["opt_out"])["text"]
        self.assertIn("authorized agent", text)
        self.assertIn("[contact address the person chose for this request]", text)
        plan = ryd.plan_law_request(self.con, pid, rights=["delete"], today=TODAY, packs=PACKS)
        self.assertEqual(plan["blocked"], ["delete"])
        self.assertTrue(any("household_inbox" in w for w in plan["warnings"]))

    def test_agent_path_unverified_warning(self) -> None:
        pid = self.person(region="UT")
        self.household(pid, mode="authorized_agent", inbox=None, inbox_permission=False)
        plan = ryd.plan_law_request(self.con, pid, rights=["delete"], today=TODAY, packs=PACKS)
        self.assertTrue(any(w.startswith("unverified: whether an agent") for w in plan["warnings"]))

    def test_switching_mode_revokes_previous_record(self) -> None:
        pid = self.person()
        first = self.household(pid)
        second = self.household(pid, mode="authorized_agent", inbox=None, inbox_permission=False)
        self.assertEqual(ryd.current_filer(self.con, pid)["id"], second)
        revoked = self.con.execute("SELECT revoked_at_utc FROM filing_authority WHERE id = ?", (first,)).fetchone()[0]
        self.assertIsNotNone(revoked)

    def test_self_mode_for_primary_only(self) -> None:
        pid = self.person(consent="self", relationship="self")
        with self.assertRaises(ValueError):
            self.household(pid)
        ryd.record_filer(self.con, pid, mode="self", filer="self", relationship="self", consent_basis="self")
        self.assertIn("I am sending this request myself", self.request(pid)["text"])

    def test_cli_record_filer_and_plan(self) -> None:
        pid = self.person()
        self.con.commit()
        ws = str(self.workspace)

        def run(*argv):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = ryd.main(list(argv))
            return code, out.getvalue(), err.getvalue()

        base = ("record-filer", "--workspace", ws, "--person-id", str(pid), "--mode", "household-inbox",
                "--filer", "spouse", "--relationship", "spouse-partner", "--consent", "subject-consent",
                "--inbox", self.INBOX)
        code, _out, err = run(*base, "--inbox-permission")
        self.assertEqual(code, 1)
        self.assertIn("consent", err)
        code, _out, err = run(*base, "--inbox-permission", "--consent-on", "2026-10-01",
                              "--consent-note", "asked me in person")
        self.assertEqual(code, 0, err)
        code, out, _ = run("law-plan", "--workspace", ws, "--person-id", str(pid))
        self.assertEqual(code, 0)
        self.assertIn("filing: household inbox", out)
        self.assertIn("not an authorized agent", out)


class CheckFilingTests(unittest.TestCase):
    def test_rules(self) -> None:
        ok = dict(mode="household_inbox", relationship="spouse_partner", consent_basis="subject_consent",
                  roster_consent="authorized_agent", inbox="a@example.com", inbox_permission=True,
                  consent_on="2026-10-01", consent_note="asked")
        self.assertEqual(laws.check_filing(**ok), [])
        self.assertTrue(laws.check_filing(**{**ok, "mode": "proxy"}))
        self.assertTrue(laws.check_filing(**{**ok, "consent_on": "Oct 1"}))
        self.assertTrue(laws.check_filing(**{**ok, "roster_consent": "self"}))
        self.assertTrue(laws.check_filing(**{**ok, "roster_consent": "unconfirmed"}))
        minor = dict(ok, relationship="parent_of_minor", consent_basis="parent_or_guardian_of_minor",
                     roster_consent="parent_of_minor", consent_on=None, consent_note=None)
        self.assertEqual(laws.check_filing(**minor), [])
        self.assertEqual(laws.check_filing(**{**minor, "mode": "guardian", "inbox": None,
                                              "inbox_permission": False}), [])
        self.assertEqual(laws.MODE_TO_SENDER["household_inbox"], "household")
        self.assertEqual(laws.agent_check(pack("CO"), ["delete"], "household"), ([], []))


if __name__ == "__main__":
    unittest.main()
