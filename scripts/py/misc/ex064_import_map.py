# EX-064 TASK A/B/J/K: scan every PE in the CODOL tree for imports of the
# iips.dll exports, plus delay imports, forwarders, and the export strings.
#
# Read-only offline static analysis. No patching, no dynamic execution.
import csv
import hashlib
import json
import os
import re
from collections import OrderedDict

import pefile

TARGETS = [
    "GetResourceManagerII",
    "GetResourceManager",
    "ReleaseResourceManagerII",
    "ReleaseResourceManager",
]
ROOT = os.path.abspath(".")


def iter_pes():
    skip = ("\\ex057_kernel.xml",)
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            if not f.lower().endswith((".dll", ".exe", ".ocx", ".sys")):
                continue
            p = os.path.join(dp, f)
            if any(s in p.lower() for s in skip):
                continue
            yield p


def main():
    rows = []
    string_hits = []
    seen_hashes = {}
    n_scanned = 0

    for path in iter_pes():
        try:
            data = open(path, "rb").read()
        except Exception:
            continue
        if len(data) < 0x100 or data[:2] != b"MZ":
            continue
        n_scanned += 1
        rel = os.path.relpath(path, ROOT)

        # ---- string search (ASCII and UTF-16LE) for the export names
        for t in TARGETS:
            for enc, needle in (("ascii", t.encode()),
                                ("utf16", t.encode("utf-16-le"))):
                st = 0
                while True:
                    i = data.find(needle, st)
                    if i < 0:
                        break
                    string_hits.append((rel, t, enc, i))
                    st = i + 1

        try:
            pe = pefile.PE(data=data, fast_load=True)
            pe.parse_data_directories(directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"],
            ])
        except Exception:
            continue

        base = pe.OPTIONAL_HEADER.ImageBase

        # ---- exports: is this module itself iips.dll or a forwarder?
        if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
            for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                nm = e.name.decode(errors="replace") if e.name else None
                if nm in TARGETS:
                    rows.append(["EXPORT", rel, "self", nm,
                                 "0x%X" % e.address, "", "", "",
                                 "STATIC_DIRECT"])

        # ---- normal imports
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            for d in pe.DIRECTORY_ENTRY_IMPORT:
                dll = d.dll.decode(errors="replace")
                for imp in d.imports:
                    nm = imp.name.decode(errors="replace") if imp.name else None
                    if nm in TARGETS:
                        rows.append(["IMPORT", rel, dll, nm,
                                     "0x%X" % (imp.address - base),
                                     "0x%X" % imp.address, "", "",
                                     "STATIC_DIRECT"])

        # ---- delay imports
        if hasattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT"):
            for d in pe.DIRECTORY_ENTRY_DELAY_IMPORT:
                dll = d.dll.decode(errors="replace")
                for imp in d.imports:
                    nm = imp.name.decode(errors="replace") if imp.name else None
                    if nm in TARGETS:
                        rows.append(["DELAY_IMPORT", rel, dll, nm,
                                     "0x%X" % (imp.address - base),
                                     "0x%X" % imp.address, "", "",
                                     "STATIC_DIRECT"])

        # ---- which modules import iips.dll at all
        all_import_dlls = []
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            all_import_dlls += [d.dll.decode(errors="replace")
                                for d in pe.DIRECTORY_ENTRY_IMPORT]
        if hasattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT"):
            all_import_dlls += [d.dll.decode(errors="replace")
                                for d in pe.DIRECTORY_ENTRY_DELAY_IMPORT]
        if any("iips" in x.lower() for x in all_import_dlls):
            rows.append(["IMPORTS_IIPS_DLL", rel,
                         ";".join(x for x in all_import_dlls
                                  if "iips" in x.lower()),
                         "", "", "", "", "", "STATIC_DIRECT"])

    print("PE files scanned: %d" % n_scanned)
    print()
    print("=" * 78)
    print("TASK B: modules referencing the iips.dll export NAMES")
    print("=" * 78)
    if not rows:
        print("  NONE")
    for r in rows:
        print("  %-14s %-58s %-22s %s" % (r[0], r[1], r[2], r[3]))

    print()
    print("=" * 78)
    print("TASK J: raw string occurrences of the export names")
    print("=" * 78)
    if not string_hits:
        print("  NONE")
    seen = set()
    for rel, t, enc, off in string_hits:
        key = (rel, t, enc)
        if key in seen:
            continue
        seen.add(key)
        cnt = sum(1 for x in string_hits if x[:3] == key)
        print("  %-58s %-24s %-6s x%d  first@0x%X" % (rel, t, enc, cnt, off))

    with open("ex064_import_map.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "module", "import_dll", "symbol", "iat_rva",
                    "iat_va", "delay_iat", "thunk_rva", "evidence"])
        w.writerows(rows)
    print()
    print("wrote ex064_import_map.csv (%d rows)" % len(rows))


if __name__ == "__main__":
    main()
