# -*- coding: utf-8 -*-
"""找 HANDOFF 里提到 239B120 / 48.5 的地方。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
SKIP = {"mem_linear", "mem_marketplace", "mem_callsign", "mem_sku",
        "__pycache__", ".git", "IIPSDownload", "main", "COD OL"}


def main():
    for base, dirs, files in os.walk(PROJ):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for fn in files:
            if not fn.lower().endswith((".md", ".txt")):
                continue
            p = os.path.join(base, fn)
            try:
                if os.path.getsize(p) > 8 * 1024 * 1024:
                    continue
                txt = open(p, "r", encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if "239B120" not in txt:
                continue
            print("== %s ==" % os.path.relpath(p, PROJ))
            for i, l in enumerate(txt.splitlines()):
                if "239B120" in l:
                    print("  %d| %s" % (i + 1, l.strip()[:160]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
