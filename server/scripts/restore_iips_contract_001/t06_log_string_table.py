"""RESTORE-IIPS-CONTRACT-001 / Task 04 - recover the provider's own log/state strings.

Task 03b found that the second ResourceManager construction site logs:

    "[ResourceManager::ResourceManager()][OK]"

iips.dll therefore carries a logging facility whose message table documents the
provider's own initialisation sequence. That table is the most direct static
evidence of the provider's internal state machine -- far stronger than guessing
what a window class name means.

This script extracts every human-readable bracketed message from the image and
classifies it, so the provider's contract is read from its own words.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")
V3 = os.path.join(ROOT, "LocalRM_v3.dll")


def printable_runs(d, minlen=8):
    out = []
    run = bytearray()
    rs = 0
    for i, c in enumerate(d):
        if 0x20 <= c < 0x7F:
            if not run:
                rs = i
            run.append(c)
        else:
            if len(run) >= minlen:
                out.append((rs, bytes(run).decode("latin1")))
            run = bytearray()
    if len(run) >= minlen:
        out.append((rs, bytes(run).decode("latin1")))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 04: provider log / state string table ===")
    print()

    for label, path in (("original_iips", IIPS), ("LocalRM_v3", V3)):
        d = open(path, "rb").read()
        runs = printable_runs(d, 8)
        bracketed = [(o, s) for o, s in runs if s.startswith("[") or "::" in s]
        rep[label] = {
            "size": len(d),
            "printable_runs_ge8": len(runs),
            "bracketed_or_doubledcolon": len(bracketed),
            "messages": [{"off": "0x%X" % o, "s": s} for o, s in bracketed],
        }
        print("%s: %d printable runs >=8, %d look like log messages"
              % (label, len(runs), len(bracketed)))
        print()
        for o, s in bracketed:
            print("   0x%-8X %s" % (o, s))
        print()

    # Compare the two providers' message tables explicitly.
    a = {m["s"] for m in rep["original_iips"]["messages"]}
    b = {m["s"] for m in rep["LocalRM_v3"]["messages"]}
    rep["only_in_original"] = sorted(a - b)
    rep["only_in_localrm"] = sorted(b - a)
    rep["shared"] = sorted(a & b)
    print("messages only in original iips.dll : %d" % len(a - b))
    for s in sorted(a - b):
        print("   - %s" % s)
    print("messages only in LocalRM_v3.dll   : %d" % len(b - a))
    for s in sorted(b - a):
        print("   + %s" % s)
    print("shared                            : %d" % len(a & b))

    with open(os.path.join(OUT, "t06_log_string_table.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t06_log_string_table.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
