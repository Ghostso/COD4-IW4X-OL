# -*- coding: utf-8 -*-
import os, hashlib, io
d = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\03_PROTOCOL"
lines = []
for f in sorted(os.listdir(d)):
    fp = os.path.join(d, f)
    if os.path.isfile(fp):
        h = hashlib.sha256()
        with open(fp, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        lines.append((f, h.hexdigest(), os.path.getsize(fp)))
out = os.path.join(d, "EARLY_SERVER_03_CHECKSUMS.txt")
with io.open(out, "w", encoding="utf-8", newline="") as fh:
    fh.write("CODOL EARLY SERVER ANALYSIS - STAGE 3 PROTOCOL CHECKSUMS (SHA-256)\n")
    fh.write("Generated (UTC): 2026-10-11\n")
    fh.write("=" * 100 + "\n")
    for f, hh, sz in lines:
        fh.write("%s  %s  %d\n" % (hh, f, sz))
for f, hh, sz in lines:
    print(hh, f, sz)
