#!/usr/bin/env python3
"""Self-check outputs. ASCII-only script.

Usage: python _cfg_verify.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = 0x331C5C0


def main():
    text = (HERE / "cfgblock_semantics.md").read_text(encoding="utf-8")
    data = json.loads((HERE / "cfgblock_fields.json").read_text(encoding="utf-8"))

    problems = []
    if "arg5 = 0x331C658" in text:
        problems.append("stale arg5 mapping")
    if "第 6 个参数" in text:
        problems.append("stale arg6 wording")
    offsets = [field["offset"] for field in data["fields"]]
    for required in ["+0x000", "+0x004", "+0x018", "+0x098", "+0x09C", "+0x4B0", "+0x538"]:
        if required not in offsets:
            problems.append("missing %s in json" % required)
    if "只有 3 个偏移" in text:
        problems.append("stale default-count wording")
    print("md_lines=%d json_fields=%d" % (len(text.splitlines()), len(offsets)))
    print("offsets=" + ",".join(offsets))
    if problems:
        print("PROBLEMS:")
        for item in problems:
            print("  " + item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
