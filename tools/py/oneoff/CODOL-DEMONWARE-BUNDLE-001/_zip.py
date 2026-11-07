# -*- coding: utf-8 -*-
import os, zipfile
ROOT  = r"D:\BaiduNetdiskDownload\使命召唤OL"
STAGE = os.path.join(ROOT, "CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012")
OUTZIP= os.path.join(ROOT, "CODOL-Demonware-Evidence-Bundle-20261012.zip")
if os.path.exists(OUTZIP):
    os.remove(OUTZIP)
n=0
with zipfile.ZipFile(OUTZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for dp, dn, fn in os.walk(STAGE):
        for f in sorted(fn):
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, os.path.dirname(STAGE)).replace("\\","/")
            z.write(p, rel); n+=1
print("entries:", n)
print("zip:", OUTZIP, os.path.getsize(OUTZIP), "bytes")
with zipfile.ZipFile(OUTZIP) as z:
    bad = z.testzip()
    print("testzip:", "OK" if bad is None else bad)
    print("entries listed:", len(z.namelist()))
