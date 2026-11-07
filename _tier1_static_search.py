"""Tier-1 pure static search (READ-ONLY).

Looks for a non-code-modifying route to get the marketplace zone / asset
registered, over the decrypted runtime image.

Usage:
  python -X utf8 _tier1_static_search.py strings <regex>
  python -X utf8 _tier1_static_search.py xref <hexva>
  python -X utf8 _tier1_static_search.py callers <hexva>

No game interaction, no memory writes, no file modification.
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(ROOT, "CODOLServer", "_mainline",
                     "_dyn100_run_20260925_182324", "live", "image_best.bin")
BASE = 0x400000


def load():
    with open(IMAGE, "rb") as f:
        return f.read()


def strings(data, rx, limit=200):
    out = []
    for m in re.finditer(rb"[\x20-\x7e]{4,200}", data):
        s = m.group(0).decode("ascii", "ignore")
        if rx.search(s):
            out.append((BASE + m.start(), s))
            if len(out) >= limit:
                break
    return out


def xref(data, target):
    """Direct call/jmp (rel32) + absolute dword references."""
    calls, abs4 = [], []
    for i in range(len(data) - 5):
        if data[i] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", data, i + 1)[0]
            if BASE + i + 5 + rel == target:
                calls.append(BASE + i)
    pat = struct.pack("<I", target)
    i = data.find(pat)
    while i != -1:
        abs4.append(BASE + i)
        i = data.find(pat, i + 1)
    return calls, abs4


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    data = load()
    cmd = argv[0]
    if cmd == "strings":
        rx = re.compile(argv[1], re.I)
        for va, s in strings(data, rx):
            print("%08X  %s" % (va, s))
        print("-- done --")
    elif cmd in ("xref", "callers"):
        target = int(argv[1], 16)
        calls, abs4 = xref(data, target)
        print("=== target %08X ===" % target)
        print("call/jmp rel32 (%d):" % len(calls))
        for va in calls[:80]:
            print("  %08X" % va)
        if cmd == "xref":
            print("absolute dword refs (%d):" % len(abs4))
            for va in abs4[:80]:
                print("  %08X" % va)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
