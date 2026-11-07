# -*- coding: utf-8 -*-
import os, hashlib, re
from pathlib import Path
ROOT=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697"
TARGETS=[b"bdCore",b"bdcore",b"BDCORE",b"bds",b"BDS",b"demonware",b"Demonware",b"DEMONWARE",
         b"CLIENTCHAL",b"clientchal",b"BDDATA",b"bddata",b"HMAC mismatch",b"hmac mismatch",
         b"Bad recv counter",b"bad recv counter",b"Bad frame/payload size",b"BADDATA",b"bdData"]
# also wide-char variants
WIDE=[]
for t in TARGETS: WIDE.append(t.decode('latin1').encode('utf-16le'))
out=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_data\sigsearch_all.txt","w",encoding="utf-8")
hits=[]; scanned=0; skipped=0
for dp,dn,fn in os.walk(ROOT):
    for f in fn:
        p=os.path.join(dp,f)
        try:
            with open(p,'rb') as fh: data=fh.read()
        except: skipped+=1; continue
        scanned+=1
        found=[]
        for t in TARGETS:
            if t in data: found.append(('ascii',t.decode('latin1')))
        for t in WIDE:
            if t in data: found.append(('wide',t.decode('utf-16le','replace')))
        if found:
            h=hashlib.sha256(data).hexdigest()
            hits.append((p,len(data),h,found))
out.write("scanned files: %d  skipped: %d  hits: %d\n\n"%(scanned,skipped,len(hits)))
for p,sz,h,found in hits:
    out.write("FILE %s\n  size=%d sha256=%s\n  hits=%s\n"%(p,sz,h,found))
out.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_data\sigsearch_all.txt",encoding="utf-8").read())
