# -*- coding: utf-8 -*-
import os, hashlib
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\06_ASSESSMENT"
files = ["EARLY_SERVER_06_FEASIBILITY_ASSESSMENT.md","EARLY_SERVER_06_MINIMAL_VALIDATION_PLAN.md"]
lines = ["# EARLY_SERVER_06 CHECKSUMS (SHA-256, 64 hex)\n"]
for fn in files:
    p=os.path.join(OUT,fn); h=hashlib.sha256(open(p,"rb").read()).hexdigest()
    lines.append(f"{h} {fn} ({os.path.getsize(p)})\n")
txt="".join(lines); open(os.path.join(OUT,"EARLY_SERVER_06_CHECKSUMS.txt"),"w",encoding="utf-8").write(txt); print(txt)
