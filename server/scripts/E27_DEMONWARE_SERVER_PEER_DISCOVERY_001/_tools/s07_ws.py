# -*- coding: utf-8 -*-
import os, hashlib, re
ROOTS=[r"D:\BaiduNetdiskDownload\使命召唤OL", r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)", r"D:\BaiduNetdiskDownload\CODOL.NET"]
TAGS=[b"BDDATA",b"CLIENTCHAL"]
EXTS={'.py','.md','.txt','.json','.js','.c','.cpp','.h','.pyc','.lua','.gsc','.cfg','.ini','.log','.csv','.jsx','.cs'}
out=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_data\bdtags_ws.txt","w",encoding="utf-8")
hits=0; scanned=0
for ROOT in ROOTS:
    for dp,dn,fn in os.walk(ROOT):
        # skip our own E2x report dirs? No - record them, but mark
        for f in fn:
            ext=os.path.splitext(f)[1].lower()
            if ext not in EXTS: continue
            p=os.path.join(dp,f)
            try:
                if os.path.getsize(p)>40_000_000: continue
                with open(p,'rb') as fh: data=fh.read()
            except: continue
            scanned+=1
            for t in TAGS:
                if t in data:
                    hits+=1
                    out.write("%s\t%s\t%s\n"%(t.decode(),p,hashlib.sha256(data).hexdigest()[:16]))
out.write("\nscanned=%d hits=%d\n"%(scanned,hits))
out.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_data\bdtags_ws.txt",encoding="utf-8").read())
