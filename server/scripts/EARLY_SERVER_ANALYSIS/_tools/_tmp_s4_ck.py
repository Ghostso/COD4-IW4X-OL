# -*- coding: utf-8 -*-
import io, os, hashlib
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\04_REUSE"
files = ["EARLY_SERVER_04_REUSE_MATRIX.csv","EARLY_SERVER_04_COMPATIBILITY_REPORT.md","EARLY_SERVER_04_BLOCKERS.md"]
lines = ["# EARLY_SERVER_04 CHECKSUMS (SHA-256, 64 hex)\n"]
for fn in files:
    p=os.path.join(OUT,fn)
    h=hashlib.sha256(open(p,"rb").read()).hexdigest()
    lines.append(f"{h} {fn} ({os.path.getsize(p)})\n")
txt="".join(lines)
open(os.path.join(OUT,"EARLY_SERVER_04_CHECKSUMS.txt"),"w",encoding="utf-8").write(txt)
print(txt)
