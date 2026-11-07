# -*- coding: utf-8 -*-
"""S2-G: build a modification timeline / hash family table for IIPS + EXE files."""
import os, sys, json, hashlib, datetime


def sha(p, n=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(n)
            if not b:
                break
            h.update(b)
    return h.hexdigest().upper()


def walk(roots, names):
    out = []
    for r in roots:
        for dp, dn, fn in os.walk(r):
            if "\\runs\\" in dp or "\\sandbox" in dp or "_observer" in dp:
                pass
            for f in fn:
                if f.lower() in names:
                    p = os.path.join(dp, f)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    out.append((p, st.st_size, st.st_mtime, sha(p)))
    return out


def main():
    names = {n.lower() for n in sys.argv[1].split(",")}
    roots = sys.argv[2].split(";")
    rows = walk(roots, names)
    rows.sort(key=lambda r: (r[3], r[2]))
    print("%-12s %-20s %-16s %s" % ("size", "mtime", "sha256[:16]", "path"))
    for p, sz, mt, h in rows:
        print("%-12d %-20s %-16s %s" % (
            sz, datetime.datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M:%S"), h[:16], p))


if __name__ == "__main__":
    main()
