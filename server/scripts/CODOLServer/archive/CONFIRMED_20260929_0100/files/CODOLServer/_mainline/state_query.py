#!/usr/bin/env python3
"""Query an AboProbe state CSV: print row transitions and selected columns.

Written because findstr/rg with several literal alternatives is unreliable in
this shell, and the state CSVs are large.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def configure_stdio() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> int:
    configure_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--contains", default=None,
                    help="only rows where any field contains this text")
    ap.add_argument("--where", action="append", default=[],
                    help="COL=VALUE filter (repeatable, exact match)")
    ap.add_argument("--cols", default=None,
                    help="comma separated column names to print")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--from-line", type=int, default=None)
    ap.add_argument("--to-line", type=int, default=None)
    a = ap.parse_args()

    path = Path(a.csv)
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    reader = csv.DictReader(text)
    rows = list(reader)
    if not rows:
        print("no rows")
        return 1

    loname = None
    for name in reader.fieldnames or []:
        if name and name.startswith("\ufeff"):
            loname = name
    if loname:
        for r in rows:
            if loname in r:
                r[loname.lstrip("\ufeff")] = r.pop(loname)

    cols = a.cols.split(",") if a.cols else list(reader.fieldnames or [])
    cols = [c.lstrip("\ufeff") for c in cols]

    filters = []
    for spec in a.where:
        key, _, value = spec.partition("=")
        filters.append((key, value))

    printed = 0
    for idx, row in enumerate(rows, start=1):
        if a.from_line and idx < a.from_line:
            continue
        if a.to_line and idx > a.to_line:
            break
        if a.contains and a.contains not in ",".join(
                str(v) for v in row.values()):
            continue
        if any(str(row.get(k, "")) != v for k, v in filters):
            continue
        print("%5d  %s" % (idx, "  ".join(
            "%s=%s" % (c, row.get(c, "")) for c in cols)))
        printed += 1
        if printed >= a.limit:
            print("... (limit %d reached)" % a.limit)
            break
    print("matched=%d total_rows=%d" % (printed, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
