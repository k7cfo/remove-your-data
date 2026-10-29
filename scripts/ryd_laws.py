#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Nick Newsom (@k7cfo) — https://github.com/k7cfo/remove-your-data
"""US state law packs: load, validate, select, compute clocks, render requests.

Stdlib only. Packs are data files under ``laws/packs``. This module never decides
that a controller is legally covered; it records what was assumed. Not legal advice.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from string import Template
from typing import Any

LAWS = Path(__file__).resolve().parent.parent / "laws"
PACKS_DIR = LAWS / "packs"
TEMPLATES_DIR = LAWS / "templates"
SCHEMA_VERSION = 1
UNIVERSAL_ID = "us-universal"

US_REGIONS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}
RIGHTS = ("access", "correct", "delete", "portability", "opt_out")
DEFAULT_RIGHTS = ("delete", "opt_out")
SENDERS = ("self", "parent", "agent")
CONSENT_TO_SENDER = {"self": "self", "parent_of_minor": "parent", "authorized_agent": "agent"}
SCOPES = ("all_personal_data", "provided_by_consumer", "collected_from_consumer", "unverified", "voluntary")
STATUSES = ("current", "superseded", "unverified")
DAY_TYPES = ("calendar", "business")
CLOCK_KEYS = ("response", "extension", "acknowledgement", "opt_out", "appeal")
TOP_KEYS = (
    "schema_version", "pack_id", "pack_version", "status", "supersedes", "superseded_by",
    "jurisdiction", "law", "verified_on", "review_by", "reviewer", "changelog", "sources",
    "applicability", "route", "rights", "deletion_scope", "clocks", "templates", "notes",
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}(?:\.\d+)?$")
ACK_RIGHTS = ("access", "correct", "delete")

RIGHT_LINES = {
    "access": "- Confirm whether you process my personal data, and give me access to it.",
    "correct": "- Correct inaccurate personal data about me.",
    "delete": "- Delete the personal data you hold about me.",
    "portability": "- Give me a copy of my personal data in a portable format.",
    "opt_out": "- Opt me out of the sale of my personal data, targeted advertising, and profiling.",
}
RIGHT_LABELS = {
    "access": "access", "correct": "correction", "delete": "deletion",
    "portability": "copy", "opt_out": "opt-out",
}


class LawError(ValueError):
    """A request cannot be planned or rendered as asked."""


# ---------------------------------------------------------------- dates


def parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not DATE_RE.match(value):
        raise LawError(f"expected YYYY-MM-DD, got {value!r}")
    return date.fromisoformat(value)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def us_federal_holidays(year: int) -> set[date]:
    """US federal holidays as observed (5 U.S.C. 6103). Business-day assumption."""
    days = {
        _observed(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),   # Birthday of Martin Luther King, Jr.
        _nth_weekday(year, 2, 0, 3),   # Washington's Birthday
        _last_weekday(year, 5, 0),     # Memorial Day
        _observed(date(year, 6, 19)),  # Juneteenth
        _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),   # Labor Day
        _nth_weekday(year, 10, 0, 2),  # Columbus Day
        _observed(date(year, 11, 11)),
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
        _observed(date(year, 12, 25)),
    }
    nxt = date(year + 1, 1, 1)
    if nxt.weekday() == 5:  # observed on Dec 31 of this year
        days.add(date(year, 12, 31))
    return days


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in us_federal_holidays(d.year)


def add_days(start: date, days: int, day_type: str) -> date:
    """Day N after ``start``. The receipt day itself is day 0."""
    if day_type == "calendar":
        return start + timedelta(days=days)
    if day_type != "business":
        raise LawError(f"unknown day_type {day_type!r}")
    d, left = start, days
    while left > 0:
        d += timedelta(days=1)
        if is_business_day(d):
            left -= 1
    return d


# ---------------------------------------------------------------- packs


def load_pack_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_packs(packs_dir: Path = PACKS_DIR) -> dict[str, dict[str, Any]]:
    packs: dict[str, dict[str, Any]] = {}
    for path in sorted(packs_dir.glob("*.json")):
        pack = load_pack_file(path)
        packs[str(pack.get("pack_id") or path.stem)] = pack
    return packs


def _clock_errors(name: str, clk: Any, source_ids: set[str]) -> list[str]:
    errs: list[str] = []
    if not isinstance(clk, dict):
        return [f"clocks.{name} must be an object or null"]
    days = clk.get("days")
    if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 366:
        errs.append(f"clocks.{name}.days must be an integer 1-366")
    if clk.get("day_type") not in DAY_TYPES:
        errs.append(f"clocks.{name}.day_type must be one of {DAY_TYPES}")
    if clk.get("source") not in source_ids:
        errs.append(f"clocks.{name}.source must name a source id")
    if not clk.get("cite"):
        errs.append(f"clocks.{name}.cite is required")
    return errs


def validate_pack(pack: Any, filename: str | None = None,
                  templates_dir: Path = TEMPLATES_DIR) -> list[str]:
    """Return a list of problems. Empty list means the pack is usable."""
    if not isinstance(pack, dict):
        return ["pack must be a JSON object"]
    errs: list[str] = []
    missing = [k for k in TOP_KEYS if k not in pack]
    if missing:
        return [f"missing keys: {', '.join(missing)}"]
    extra = sorted(set(pack) - set(TOP_KEYS))
    if extra:
        errs.append(f"unknown keys: {', '.join(extra)}")
    if pack["schema_version"] != SCHEMA_VERSION:
        errs.append(f"schema_version must be {SCHEMA_VERSION}")
    pid = pack["pack_id"]
    if not isinstance(pid, str) or not re.match(r"^us-(?:[a-z]{2}(?:-[a-z0-9]+)?|universal)$", pid):
        errs.append("pack_id must look like us-xx, us-xx-<suffix> (a replacing law) or us-universal")
    if filename and Path(filename).stem != pid:
        errs.append(f"file name {filename} does not match pack_id {pid}")
    if not isinstance(pack["pack_version"], str) or not VERSION_RE.match(pack["pack_version"]):
        errs.append("pack_version must be YYYY.MM.DD[.n]")
    if pack["status"] not in STATUSES:
        errs.append(f"status must be one of {STATUSES}")
    if pack["status"] == "superseded" and not pack["superseded_by"]:
        errs.append("superseded pack must name superseded_by")
    for key in ("verified_on", "review_by"):
        if not isinstance(pack[key], str) or not DATE_RE.match(pack[key]):
            errs.append(f"{key} must be YYYY-MM-DD")
    if not errs and pack["review_by"] <= pack["verified_on"]:
        errs.append("review_by must be after verified_on")
    jur = pack["jurisdiction"]
    universal = pid == UNIVERSAL_ID
    if not isinstance(jur, dict) or jur.get("country") != "US":
        errs.append("jurisdiction.country must be US")
    elif universal:
        if jur.get("region") != "*":
            errs.append("universal pack region must be *")
    elif jur.get("region") not in US_REGIONS or pid.split("-")[1] != str(jur.get("region")).lower():
        errs.append("jurisdiction.region must be a US state code matching pack_id")
    rev = pack["reviewer"]
    if not isinstance(rev, dict) or not rev.get("handle") or "legal_review" not in rev:
        errs.append("reviewer needs handle and legal_review")
    log = pack["changelog"]
    if not isinstance(log, list) or not log:
        errs.append("changelog must be a non-empty list")
    elif not any(isinstance(e, dict) and e.get("version") == pack["pack_version"] for e in log):
        errs.append("changelog needs an entry for pack_version")
    sources = pack["sources"]
    source_ids: set[str] = set()
    if not isinstance(sources, list):
        errs.append("sources must be a list")
        sources = []
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            errs.append(f"sources[{i}] must be an object")
            continue
        sid = s.get("id")
        if not sid or sid in source_ids:
            errs.append(f"sources[{i}].id missing or duplicate")
        source_ids.add(str(sid))
        if not str(s.get("url", "")).startswith("https://"):
            errs.append(f"sources[{i}].url must be https")
        if not DATE_RE.match(str(s.get("checked_on", ""))):
            errs.append(f"sources[{i}].checked_on must be YYYY-MM-DD")
        if not SHA_RE.match(str(s.get("sha256", ""))):
            errs.append(f"sources[{i}].sha256 must be 64 lowercase hex")
        if not s.get("title"):
            errs.append(f"sources[{i}].title is required")
    app = pack["applicability"]
    if not isinstance(app, dict) or not isinstance(app.get("narrow"), bool) or not app.get("summary"):
        errs.append("applicability needs summary and narrow (bool)")
    elif not isinstance(app.get("attestations_required"), list):
        errs.append("applicability.attestations_required must be a list")
    if pack["route"] not in (None, "drop_first"):
        errs.append("route must be null or drop_first")
    rights = pack["rights"]
    if not isinstance(rights, dict) or set(rights) != set(RIGHTS):
        errs.append(f"rights must have exactly {RIGHTS}")
    else:
        for name, r in rights.items():
            if not isinstance(r, dict) or not isinstance(r.get("available"), bool):
                errs.append(f"rights.{name}.available must be bool")
            elif r.get("authorized_agent") not in (True, False, None):
                errs.append(f"rights.{name}.authorized_agent must be true, false or null")
    scope = pack["deletion_scope"]
    if not isinstance(scope, dict) or scope.get("value") not in SCOPES:
        errs.append(f"deletion_scope.value must be one of {SCOPES}")
    elif not universal and scope.get("source") not in source_ids:
        errs.append("deletion_scope.source must name a source id")
    clocks = pack["clocks"]
    if not isinstance(clocks, dict) or set(clocks) != set(CLOCK_KEYS):
        errs.append(f"clocks must have exactly {CLOCK_KEYS}")
    else:
        if universal:
            for k in ("response", "extension", "acknowledgement", "opt_out"):
                if clocks[k] is not None:
                    errs.append(f"universal pack must not set clocks.{k}")
        else:
            for k in ("response", "extension"):
                if clocks[k] is None:
                    errs.append(f"clocks.{k} is required")
        for k in ("response", "extension", "acknowledgement", "opt_out"):
            if clocks[k] is not None:
                errs.extend(_clock_errors(k, clocks[k], source_ids))
        ap = clocks["appeal"]
        if not isinstance(ap, dict) or not isinstance(ap.get("available"), bool):
            errs.append("clocks.appeal.available must be bool")
        elif ap["available"]:
            if universal:
                errs.append("universal pack cannot have an appeal clock")
            errs.extend(_clock_errors("appeal.response", ap.get("response"), source_ids))
            if ap.get("extension") is not None:
                errs.extend(_clock_errors("appeal.extension", ap["extension"], source_ids))
            if "days" in ap or isinstance(ap.get("consumer_filing_window"), int):
                errs.append("appeal filing window must not be a number (statutes say reasonable period)")
    law = pack["law"]
    if universal:
        if law is not None or sources:
            errs.append("universal pack must have law null and no sources")
    elif not isinstance(law, dict):
        errs.append("law must be an object")
    else:
        for k in ("name", "citation", "law_version", "effective_date", "effective_date_source"):
            if not law.get(k):
                errs.append(f"law.{k} is required")
        if law.get("effective_date") and not DATE_RE.match(str(law["effective_date"])):
            errs.append("law.effective_date must be YYYY-MM-DD")
        if law.get("effective_date_source") and law["effective_date_source"] not in source_ids:
            errs.append("law.effective_date_source must name a source id")
    tpl = pack["templates"]
    if not isinstance(tpl, dict) or not tpl.get("request"):
        errs.append("templates.request is required")
    else:
        for k in ("request", "appeal"):
            tid = tpl.get(k)
            if tid and not (templates_dir / f"{tid}.txt").exists():
                errs.append(f"templates.{k} {tid} has no file")
        if not universal and isinstance(clocks, dict) and isinstance(clocks.get("appeal"), dict) \
                and clocks["appeal"].get("available") and not tpl.get("appeal"):
            errs.append("templates.appeal is required when an appeal exists")
    if not isinstance(pack["notes"], list):
        errs.append("notes must be a list")
    return errs


def validate_dir(packs_dir: Path = PACKS_DIR, templates_dir: Path = TEMPLATES_DIR) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    packs: dict[str, dict[str, Any]] = {}
    for path in sorted(packs_dir.glob("*.json")):
        try:
            pack = load_pack_file(path)
        except (OSError, json.JSONDecodeError) as exc:
            out[path.name] = [f"unreadable: {exc}"]
            continue
        out[path.name] = validate_pack(pack, path.name, templates_dir)
        if isinstance(pack, dict) and isinstance(pack.get("pack_id"), str):
            packs[pack["pack_id"]] = pack
    if UNIVERSAL_ID not in packs:
        out.setdefault("(set)", []).append("us-universal pack is missing")
    for pid, pack in packs.items():
        nxt = pack.get("superseded_by")
        if nxt and nxt not in packs:
            out.setdefault(f"{pid}.json", []).append(f"superseded_by {nxt} not found")
    return out


# ---------------------------------------------------------------- selection


@dataclass
class Selection:
    region: str
    pack: dict[str, Any]
    universal: bool
    reason: str
    warnings: list[str] = field(default_factory=list)

    @property
    def pack_ref(self) -> str:
        return f"{self.pack['pack_id']}@{self.pack['pack_version']}"


def is_stale(pack: dict[str, Any], today: date) -> bool:
    return today > parse_date(pack["review_by"])


def select_pack(
    packs: dict[str, dict[str, Any]],
    region: str,
    *,
    on: date,
    today: date,
    attested: bool,
    controller_covered: bool = False,
    force_universal: bool = False,
) -> Selection:
    """Pick the state pack, or fall back to universal wording with a reason."""
    region = (region or "").upper()
    if region not in US_REGIONS:
        raise LawError(f"{region or '(none)'} is not a US state or DC; use the non-US path")
    universal = packs.get(UNIVERSAL_ID)
    if universal is None:
        raise LawError("us-universal pack is missing")

    def fallback(reason: str, *warn: str) -> Selection:
        return Selection(region, universal, True, reason, list(warn))

    if force_universal:
        return fallback("requested_universal")
    pack = packs.get(f"us-{region.lower()}")
    hops = 0
    while pack and pack.get("status") == "superseded" and hops < 5:
        nxt = packs.get(str(pack.get("superseded_by")))
        if not nxt:
            return fallback("superseded", f"{pack['pack_id']}@{pack['pack_version']} is superseded and its replacement is missing")
        pack, hops = nxt, hops + 1
    if not pack:
        return fallback("no_pack", f"No law pack for {US_REGIONS[region]}; using voluntary wording.")
    if pack.get("status") != "current":
        return fallback(pack.get("status", "unverified"), f"{pack['pack_id']} is not marked current.")
    if validate_pack(pack):
        return fallback("invalid_pack", f"{pack['pack_id']} failed validation.")
    if is_stale(pack, today):
        return fallback("stale", f"{pack['pack_id']} review date {pack['review_by']} has passed; re-verify before citing it.")
    if on < parse_date(pack["law"]["effective_date"]):
        return fallback("not_yet_effective", f"{pack['law']['name']} is not in effect until {pack['law']['effective_date']}.")
    if not attested:
        return fallback("no_attestation", f"No residency attestation for {US_REGIONS[region]}; record one with attest-residency.")
    if pack["applicability"]["narrow"] and not controller_covered:
        return fallback("narrow_law", pack["applicability"]["summary"])
    sel = Selection(region, pack, False, "state_pack")
    if pack.get("route") == "drop_first":
        sel.warnings.append("California resident: file CA DROP first (SKILL.md section 8). Use this for businesses DROP does not reach.")
    return sel


# ---------------------------------------------------------------- clocks


def _clock(name: str, start: date, clk: dict[str, Any], pack: dict[str, Any], *,
           extra_days: int = 0) -> dict[str, Any]:
    due = add_days(start, clk["days"], clk["day_type"])
    if extra_days:
        due = add_days(due, extra_days, "calendar")
    src = {s["id"]: s for s in pack["sources"]}.get(clk["source"], {})
    return {
        "name": name, "start": start.isoformat(), "due": due.isoformat(),
        "days": clk["days"] + extra_days, "day_type": clk["day_type"],
        "cite": clk["cite"], "source_url": src.get("url"),
    }


def compute_clocks(pack: dict[str, Any], received_on: date | str,
                   rights: list[str] | tuple[str, ...], *, extended: bool = False) -> list[dict[str, Any]]:
    """Statutory clocks counted from the controller's receipt date."""
    received = parse_date(received_on)
    c = pack["clocks"]
    if c.get("response") is None:
        return []
    out: list[dict[str, Any]] = []
    if c.get("acknowledgement") and any(r in ACK_RIGHTS for r in rights):
        out.append(_clock("acknowledgement", received, c["acknowledgement"], pack))
    if c.get("opt_out") and "opt_out" in rights:
        out.append(_clock("opt_out", received, c["opt_out"], pack))
    resp_rights = [r for r in rights if not (r == "opt_out" and c.get("opt_out"))]
    if resp_rights:
        if extended:
            ext = c["extension"]
            row = _clock("extended_response", received, c["response"], pack, extra_days=ext["days"])
            row["cite"] = f"{c['response']['cite']}; extension {ext['cite']}"
            out.append(row)
        else:
            out.append(_clock("response", received, c["response"], pack))
    return out


def extension_allowed(pack: dict[str, Any], received_on: date | str, notice_on: date | str) -> bool:
    """An extension counts only if the controller gave notice within the first period."""
    resp = pack["clocks"]["response"]
    if resp is None:
        return False
    initial_due = add_days(parse_date(received_on), resp["days"], resp["day_type"])
    return parse_date(notice_on) <= initial_due


def appeal_clock(pack: dict[str, Any], appeal_received_on: date | str, *,
                 extended: bool = False) -> dict[str, Any]:
    ap = pack["clocks"]["appeal"]
    if not ap.get("available"):
        raise LawError(f"{pack['pack_id']} has no statutory appeal: {ap.get('note', '')}".strip())
    start = parse_date(appeal_received_on)
    if extended:
        if not ap.get("extension"):
            raise LawError(f"{pack['pack_id']} appeal has no extension")
        row = _clock("appeal_extended", start, ap["response"], pack, extra_days=ap["extension"]["days"])
        return row
    return _clock("appeal", start, ap["response"], pack)


# ---------------------------------------------------------------- agents


def agent_check(pack: dict[str, Any], rights: list[str], sender: str) -> tuple[list[str], list[str]]:
    """(blocked, unknown) rights for an authorized-agent sender under a state pack."""
    if sender != "agent" or pack["pack_id"] == UNIVERSAL_ID:
        return [], []
    blocked = [r for r in rights if pack["rights"][r]["authorized_agent"] is False]
    unknown = [r for r in rights if pack["rights"][r]["authorized_agent"] is None]
    return blocked, unknown


def parse_rights(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_RIGHTS)
    out: list[str] = []
    for part in raw.split(","):
        r = part.strip().lower().replace("-", "_")
        if r not in RIGHTS:
            raise LawError(f"unknown right {part!r}; choose from {', '.join(RIGHTS)}")
        if r not in out:
            out.append(r)
    return out


# ---------------------------------------------------------------- rendering


def _template(tid: str, templates_dir: Path) -> Template:
    return Template((templates_dir / f"{tid}.txt").read_text(encoding="utf-8"))


def _sender_block(sender: str, universal: bool) -> str:
    if sender == "parent":
        return ("I am the parent or legal guardian of the minor named below and am sending "
                "this on their behalf.")
    if sender == "agent":
        if universal:
            return "I am helping the person named below send this request, with their permission."
        return ("I am sending this as the consumer's authorized agent. I can provide proof of "
                "my authority on request.")
    return "I am sending this request myself."


def _scope_block(pack: dict[str, Any], rights: list[str]) -> str:
    if "delete" not in rights:
        return ""
    scope = pack["deletion_scope"]["value"]
    if scope in ("provided_by_consumer", "collected_from_consumer"):
        what = "I provided to you" if scope == "provided_by_consumer" else "you collected from me"
        return (f"\nThe deletion right in that law may cover only personal data {what}. I also ask "
                "you, voluntarily, to delete personal data about me that you obtained from other "
                "sources, and to opt me out of any sale or sharing of it.\n")
    if pack["jurisdiction"]["region"] == "OR":
        return ("\nIf you obtained my data from another source and keep a minimal record instead "
                "of deleting it, please also opt me out of any processing of it beyond that record.\n")
    return ""


def _timing_block(pack: dict[str, Any], rights: list[str]) -> str:
    c = pack["clocks"]
    resp, ext = c["response"], c["extension"]
    unit = "business days" if resp["day_type"] == "business" else "days"
    lines = [
        f"\nAs I read that law, a controller responds within {resp['days']} {unit} of receiving "
        f"a request and may extend that once by up to {ext['days']} more days when reasonably "
        f"necessary, if it tells me within the first {resp['days']} {unit}."
    ]
    if c.get("acknowledgement") and any(r in ACK_RIGHTS for r in rights):
        a = c["acknowledgement"]
        lines.append(f"It also confirms receipt within {a['days']} {a['day_type']} days.")
    if c.get("opt_out") and "opt_out" in rights:
        o = c["opt_out"]
        lines.append(f"Opt-out requests are acted on within {o['days']} {o['day_type']} days.")
    return " ".join(lines) + "\n"


def _appeal_block(pack: dict[str, Any]) -> str:
    if pack["clocks"]["appeal"].get("available"):
        return "\nIf you decline to act on any part of this request, please tell me why and how to appeal.\n"
    return ""


def _tidy(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def render_request(sel: Selection, *, controller: str, name: str, rights: list[str],
                   sender: str, templates_dir: Path = TEMPLATES_DIR) -> tuple[str, str]:
    """Return (template_id, text)."""
    if sender not in SENDERS:
        raise LawError(f"sender must be one of {SENDERS}")
    pack = sel.pack
    tid = pack["templates"]["request"]
    rights_block = "\n".join(RIGHT_LINES[r] for r in rights)
    if sel.universal:
        text = _template(tid, templates_dir).substitute(
            controller=controller, rights_block="Specifically:\n" + rights_block,
            sender_block=_sender_block(sender, True), name=name,
        )
        return tid, _tidy(text)
    blocked, _unknown = agent_check(pack, rights, sender)
    if blocked:
        raise LawError(
            f"{pack['law']['name']} does not let an authorized agent submit: {', '.join(blocked)}. "
            "Have the person send those themselves, drop them with --rights, or use --universal."
        )
    text = _template(tid, templates_dir).substitute(
        controller=controller, state=US_REGIONS[sel.region], law_name=pack["law"]["name"],
        citation=pack["law"]["citation"],
        rights_label=", ".join(RIGHT_LABELS[r] for r in rights),
        rights_block=rights_block, scope_block=_scope_block(pack, rights),
        timing_block=_timing_block(pack, rights), appeal_block=_appeal_block(pack),
        sender_block=_sender_block(sender, False), name=name,
    )
    return tid, _tidy(text)


def render_appeal(pack: dict[str, Any], region: str, *, controller: str, name: str,
                  received_on: str, sender: str, templates_dir: Path = TEMPLATES_DIR) -> tuple[str, str]:
    ap = pack["clocks"]["appeal"]
    if not ap.get("available"):
        raise LawError(f"{pack['pack_id']} has no statutory appeal")
    tid = pack["templates"]["appeal"]
    r = ap["response"]
    timing = (f"As I read that law, a controller tells me in writing what it did in response to an "
              f"appeal within {r['days']} days of receiving it")
    if ap.get("extension"):
        timing += f", and may extend that by up to {ap['extension']['days']} more days when reasonably necessary"
    timing += ".\n"
    text = _template(tid, templates_dir).substitute(
        controller=controller, state=US_REGIONS[region], law_name=pack["law"]["name"],
        citation=pack["law"]["citation"], received_on=received_on, timing_block=timing,
        sender_block=_sender_block(sender, False), name=name,
    )
    return tid, _tidy(text)


def assumptions(sel: Selection, *, sender: str, controller_covered: bool) -> list[str]:
    out = ["Not legal advice. Wording and clocks come from the pack, not from a lawyer."]
    if sel.universal:
        out.append(f"Voluntary request ({sel.reason}); no statutory deadline is tracked.")
        return out
    p = sel.pack
    out.append(f"Pack {sel.pack_ref}, law {p['law']['name']} {p['law']['law_version']}, verified {p['verified_on']}.")
    out.append("Assumes the controller is subject to the law; not checked against its thresholds or exemptions."
               if not controller_covered else
               "User asserted the controller is subject to the law; not independently checked.")
    out.append("Clocks count from the date the controller received the request, as recorded by the user.")
    days = {c["day_type"] for c in p["clocks"].values() if isinstance(c, dict) and "day_type" in c}
    if "business" in days:
        out.append("Business days skip weekends and US federal holidays; state holidays are not modeled.")
    if sender == "agent":
        out.append("Sent by an authorized agent; controller may verify the agent's authority.")
    return out


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
