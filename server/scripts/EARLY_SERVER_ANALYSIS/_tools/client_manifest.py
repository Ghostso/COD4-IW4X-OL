# -*- coding: utf-8 -*-
"""EARLY_SERVER_00 client-side manifest (the rest of the early build).

Hashes everything under CODOL_Client and the launcher, excluding the server
subtree (already covered).  Read-only.
"""
import hashlib, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

CHUNK = 1 << 20

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b: break
            h.update(b)
    return h.hexdigest()

def main():
    root = sys.argv[1]
    out = sys.argv[2]
    root = os.path.abspath(root)
    files = []
    for dp, dn, fn in os.walk(root):
        for n in fn:
            full = os.path.join(dp, n)
            try: st = os.stat(full)
            except OSError: continue
            files.append((os.path.relpath(full, root), full, st.st_size, st.st_mtime))
    files.sort(key=lambda x: x[0].lower())
    res = {}
    def work(it):
        rel, full, sz, mt = it
        try: return rel, (sha256(full), sz, mt)
        except OSError as e: return rel, ("", sz, mt)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for rel, v in pool.map(work, files):
            res[rel] = v
    total = 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        f.write("relpath,size,sha256,mtime_utc\n")
        for rel, full, sz, mt in files:
            d, s, m = res[rel]
            total += s
            f.write('%s,%d,%s,%s\n' % (rel.replace(",", "%2C"), s, d,
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(m))))
    print(json.dumps({"files": len(files), "bytes": total,
                      "mib": round(total/(1<<20),2)}, indent=2))

if __name__ == "__main__":
    main()
