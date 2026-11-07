# -*- coding: utf-8 -*-
import hashlib, os, sys
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\XVAL-01_LOCAL_NETWORK_EVIDENCE_CROSS_VALIDATION"
MAN = os.path.join(OUT, "SHA256SUMS.txt")
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<20), b""): h.update(b)
    return h.hexdigest()
targets=[]
for dp,dn,fs in os.walk(OUT):
    for fn in sorted(fs):
        p=os.path.join(dp,fn)
        if os.path.abspath(p)==os.path.abspath(MAN): continue
        targets.append(p)
targets.sort()
lines=[]
for p in targets:
    rel=os.path.relpath(p,OUT).replace("\\","/")
    lines.append(f"{sha(p)}  {rel}")
with open(MAN,"w",encoding="utf-8",newline="\n") as f:
    f.write("\n".join(lines)+"\n")
print(f"manifest entries: {len(lines)}")
