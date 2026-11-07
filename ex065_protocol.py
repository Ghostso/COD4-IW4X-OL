# EX-065 PHASE 3/5: recover the TCLS<->CODOL context protocol from the
# modules that actually contain the artifacts.
import json
import os
import re

ROOT = os.path.abspath(".")

TARGETS = [
    ("WeGame\\tcls\\tcls_core.exe", "tcls_core.exe"),
    ("COD OL\\TCLS\\Tenio\\TCLS.dll", "TCLS.dll"),
    ("COD OL\\TCLS\\ClientBase.dll", "ClientBase.dll"),
    ("COD OL\\TCLS\\tpsvcBase.dll", "tpsvcBase.dll"),
    ("COD OL\\codoMP_client_shipRetailBase.dll", "Base.dll"),
    ("CODOLLauncher\\CODOLLauncher.exe", "CODOLLauncher.exe"),
]

KEYS = [
    b"TCLS_SHAREDMEMEMORY", b"GamePID", b"gamepid", b"codoMP_client_shipRetail",
    b"tcls_core.exe", b"TCLS", b"WeGame", b"IIPS", b"CODOL",
]


def show_strings(label, data):
    print("  -- %s --" % label)
    for s in KEYS:
        for enc, needle in (("ascii", s), ("utf16",
                                           s.decode(errors="replace")
                                           .encode("utf-16-le"))):
            st = 0
            while True:
                i = data.find(needle, st)
                if i < 0:
                    break
                # capture surrounding printable context
                lo = max(0, i - 48)
                hi = min(len(data), i + len(needle) + 48)
                print("     %-28s %-6s @0x%X  ctx=%r" % (
                    s.decode(errors="replace"), enc, i,
                    data[lo:hi].replace(b"\x00", b".")))
                st = i + 1


def main():
    for rel, label in TARGETS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print("MISSING %s" % rel)
            continue
        data = open(p, "rb").read()
        print("=" * 78)
        print("%s  (%s)  size %d" % (label, rel, len(data)))
        print("=" * 78)
        show_strings(label, data)
        print()


if __name__ == "__main__":
    main()
