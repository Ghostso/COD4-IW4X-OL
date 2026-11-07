"""Dump the two live provider objects identified by PTR_TRACK.

PTR_TRACK gave stable pointers; this script records the offsets we need to
distinguish "key buffer" from "decoy certificate data":
    +0x00 vtable, +0x04/+0x08 lengths, +0x0C ctx, +0x14 key, +0x9C schedule
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    stdout = Path(sys.argv[1])
    text = stdout.read_text(encoding="utf-8", errors="replace")
    ptrs = re.findall(r"PTR_TRACK,t=[\d.]+ p604=(\d+) p608=(\d+),h604=([0-9a-f]*),"
                      r"h608=([0-9a-f]*)", text)
    if not ptrs:
        print("no PTR_TRACK records")
        return 1
    seen = []
    for p604, p608, h604, h608 in ptrs:
        if (p604, p608) not in seen and p604 != "0":
            seen.append((p604, p608))
            print(f"p604=0x{int(p604):08X} p608=0x{int(p608):08X}")
            print(f"  h604={h604}")
            print(f"  h608={h608}")
    print("distinct non-zero pointer pairs:", len(seen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
