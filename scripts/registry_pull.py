#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Diff the California data-broker registry CSV against references/brokers.md.

Stdlib only. Prints hostnames in the registry that are not already in the
explicit queue. Does **not** add rows, POST forms, or spray opt-outs.

DROP still covers registered CA brokers for CA residents. Public people-search
pages are filed one-by-one. Registry membership is not a filing queue.

Usage:
  python3 scripts/registry_pull.py
  python3 scripts/registry_pull.py --csv https://cppa.ca.gov/data_broker_registry/registry.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
BROKERS = REPO / "references" / "brokers.md"
STATUS = REPO / "STATUS.md"
DEAD = REPO / "references" / "dead-urls.md"

CA_CSV = "https://cppa.ca.gov/data_broker_registry/registry.csv"
CA_CSV_PREV = "https://cppa.ca.gov/data_broker_registry/registry2025.csv"

HOST_RE = re.compile(
    r"https?://[^\s)|]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
)


def host_of(value: str) -> str:
    text = value.strip().strip(")`]").strip()
    if not text:
        return ""
    if "://" not in text:
        if "@" in text:
            text = text.rsplit("@", 1)[-1]
        if "/" in text:
            text = text.split("/", 1)[0]
        host = text.lower()
    else:
        host = (urlparse(text).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in {"http", "https"}:
        return ""
    return host


def hosts_in_text(path: Path) -> set[str]:
    if not path.exists():
        return set()
    found: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        for match in HOST_RE.findall(raw):
            host = host_of(match)
            if host:
                found.add(host)
    return found


def fetch_csv(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "remove-your-data registry_pull (stdlib)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def hosts_from_csv(body: str) -> set[str]:
    sample = body[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(body), dialect=dialect)
    hosts: set[str] = set()
    if not reader.fieldnames:
        return hosts
    fields = [f for f in reader.fieldnames if f]
    urlish = [
        f
        for f in fields
        if re.search(r"url|site|web|domain|host", f, re.I)
    ]
    use = urlish or fields
    for row in reader:
        for key in use:
            val = (row.get(key) or "").strip()
            if not val:
                continue
            host = host_of(val)
            if host:
                hosts.add(host)
    return hosts


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", default=CA_CSV, help="Registry CSV URL or local path")
    p.add_argument(
        "--fallback",
        default=CA_CSV_PREV,
        help="Second CSV if the first is empty or fails",
    )
    args = p.parse_args(argv)

    known = hosts_in_text(BROKERS) | hosts_in_text(STATUS) | hosts_in_text(DEAD)
    src = args.csv
    body = ""
    tried = [src]
    path = Path(src)
    try:
        body = path.read_text(encoding="utf-8") if path.exists() else fetch_csv(src)
    except Exception as exc:
        print(f"# failed {src}: {exc}", file=sys.stderr)
        if args.fallback and args.fallback != src:
            tried.append(args.fallback)
            fb = Path(args.fallback)
            try:
                body = (
                    fb.read_text(encoding="utf-8")
                    if fb.exists()
                    else fetch_csv(args.fallback)
                )
                src = args.fallback
            except Exception as exc2:
                print(f"# failed {args.fallback}: {exc2}", file=sys.stderr)
                return 1

    registry = hosts_from_csv(body)
    if not registry and args.fallback and src != args.fallback:
        print(f"# empty {src}; trying {args.fallback}", file=sys.stderr)
        try:
            body = fetch_csv(args.fallback)
            src = args.fallback
            registry = hosts_from_csv(body)
        except Exception as exc:
            print(f"# failed {args.fallback}: {exc}", file=sys.stderr)
            return 1

    missing = sorted(h for h in registry if h not in known)
    print(f"# source {src}")
    print(f"# registry hosts {len(registry)}")
    print(f"# already in queue/status/dead {len(registry & known)}")
    print(f"# not in explicit queue {len(missing)}")
    print("# Do not POST a generic form to these rows. Confirm a live people-search")
    print("# opt-out URL before adding. DROP covers CA-registered brokers for CA residents.")
    for host in missing:
        print(host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
