# EX-064 TASK I/K: who loads IIPSLaunchRestore.dll, and are its exports the
# entry point?
import json
import os
import re

import pefile

ROOT = os.path.abspath(".")
TARGET_DLLS = [b"IIPSLaunchRestore.dll", b"IIPSLaunchRestore",
               b"CreateIIPSRepair", b"RealeaseIIPSRepair"]


def main():
    print("=" * 78)
    print("who references IIPSLaunchRestore.dll / its exports?")
    print("=" * 78)
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            if not f.lower().endswith((".dll", ".exe")):
                continue
            p = os.path.join(dp, f)
            if "IIPSLaunchRestore" in f:
                continue
            try:
                data = open(p, "rb").read()
            except Exception:
                continue
            if data[:2] != b"MZ":
                continue
            rel = os.path.relpath(p, ROOT)
            for t in TARGET_DLLS:
                for enc, needle in (("ascii", t), ("utf16", t.decode()
                                                    .encode("utf-16-le"))):
                    st = 0
                    c = 0
                    first = None
                    while True:
                        i = data.find(needle, st)
                        if i < 0:
                            break
                        if first is None:
                            first = i
                        c += 1
                        st = i + 1
                    if c:
                        print("  %-58s %-24s %-6s x%d @0x%X" % (
                            rel, t.decode(), enc, c, first))

    print()
    print("=" * 78)
    print("IIPSLaunchRestore.dll exports again + importers of iips by name")
    print("=" * 78)
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            if not f.lower().endswith((".dll", ".exe")):
                continue
            p = os.path.join(dp, f)
            if "IIPSLaunchRestore" in f:
                continue
            try:
                pe = pefile.PE(p, fast_load=True)
                pe.parse_data_directories()
            except Exception:
                continue
            rel = os.path.relpath(p, ROOT)
            names = []
            if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                names += [d.dll.decode(errors="replace")
                          for d in pe.DIRECTORY_ENTRY_IMPORT]
            if hasattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT"):
                names += [d.dll.decode(errors="replace")
                          for d in pe.DIRECTORY_ENTRY_DELAY_IMPORT]
            for n in names:
                if "LaunchRestore" in n:
                    print("  IMPORT %-58s -> %s" % (rel, n))


if __name__ == "__main__":
    main()
