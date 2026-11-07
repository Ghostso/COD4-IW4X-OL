# EX-065 PHASE 3/4: scan the whole CODOL/WeGame tree for the TCLS<->CODOL
# context artifacts and for whoever creates tcls_core.exe.
import hashlib
import os
import re

ROOT = os.path.abspath(".")

CTX_STRINGS = [
    b"TCLS_SHAREDMEMEMORY", b"TCLS_SHAREDMEMORY", b"SHAREDMEMEMORY",
    b"GamePID", b"gamepid", b"GAMEPID", b"codoMP_client_shipRetail",
    b"tcls_core.exe", b"CreateIIPSRepair", b"IIPSLaunchRestore.dll",
]


def main():
    print("=" * 78)
    print("scan of the whole tree for the TCLS<->CODOL context artifacts")
    print("=" * 78)
    n = 0
    hits = {}
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                sz = os.path.getsize(p)
            except Exception:
                continue
            if sz < 32 or sz > 300 * 1024 * 1024:
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext not in (".exe", ".dll", ".ini", ".cfg", ".xml", ".txt",
                           ".json", ".dat", ".bin", ".log"):
                continue
            try:
                data = open(p, "rb").read()
            except Exception:
                continue
            n += 1
            rel = os.path.relpath(p, ROOT)
            for s in CTX_STRINGS:
                for enc, needle in (("ascii", s),
                                    ("utf16", s.decode(errors="replace")
                                     .encode("utf-16-le"))):
                    if needle in data:
                        hits.setdefault(s.decode(errors="replace"), []).append(
                            (rel, enc))

    print("files scanned: %d" % n)
    for k in [s.decode(errors="replace") for s in CTX_STRINGS]:
        v = hits.get(k, [])
        print()
        print("  %-30s : %d files" % (k, len(v)))
        seen = set()
        for rel, enc in v:
            if (rel, enc) in seen:
                continue
            seen.add((rel, enc))
            print("      %-70s %s" % (rel, enc))


if __name__ == "__main__":
    main()
