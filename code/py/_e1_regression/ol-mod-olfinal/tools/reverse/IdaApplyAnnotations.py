"""Apply reviewed names and comments to an IDA database from JSON.

Usage:
  idat.exe -A -S"IdaApplyAnnotations.py annotations.json" target.i64
"""

from __future__ import annotations

import json
import pathlib

import ida_auto
import ida_bytes
import ida_name
import ida_pro
import idc


def main() -> None:
    arguments = list(idc.ARGV[1:])
    if len(arguments) != 1:
        raise SystemExit("usage: IdaApplyAnnotations.py ANNOTATIONS.json")

    source = pathlib.Path(arguments[0])
    document = json.loads(source.read_text(encoding="utf-8"))
    ida_auto.auto_wait()

    failures: list[str] = []
    applied = 0
    for entry in document.get("annotations", []):
        address = int(str(entry["address"]), 0)
        name = entry.get("name")
        comment = entry.get("comment")
        if name and not ida_name.set_name(address, name, ida_name.SN_FORCE):
            failures.append(f"could not name 0x{address:X} as {name}")
            continue
        if comment and not ida_bytes.set_cmt(address, comment, False):
            failures.append(f"could not comment 0x{address:X}")
            continue
        applied += 1

    print(f"Applied {applied} annotations from {source}")
    for failure in failures:
        print(f"ERROR: {failure}")
    ida_pro.qexit(1 if failures else 0)


if __name__ == "__main__":
    main()
