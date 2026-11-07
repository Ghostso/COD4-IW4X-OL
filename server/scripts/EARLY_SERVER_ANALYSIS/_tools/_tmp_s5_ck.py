# -*- coding: utf-8 -*-
import os, hashlib
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\05_DIFF"
files = ["EARLY_SERVER_05_CURRENT_CODOL_DIFF.md","EARLY_SERVER_05_REUSE_CANDIDATES.csv","EARLY_SERVER_05_SHORTEST_PATH.md"]
lines = ["# EARLY_SERVER_05 CHECKSUMS (SHA-256, 64 hex)\n"]
for fn in files:
    p=os.path.join(OUT,fn); h=hashlib.sha256(open(p,"rb").read()).hexdigest()
    lines.append(f"{h} {fn} ({os.path.getsize(p)})\n")
txt="".join(lines); open(os.path.join(OUT,"EARLY_SERVER_05_CHECKSUMS.txt"),"w",encoding="utf-8").write(txt); print(txt)
