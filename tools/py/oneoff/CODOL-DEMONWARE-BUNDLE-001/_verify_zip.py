# -*- coding: utf-8 -*-
import os, zipfile, hashlib
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL"
Z=os.path.join(ROOT,"CODOL-Demonware-Evidence-Bundle-20261012.zip")
with zipfile.ZipFile(Z) as z:
    names=z.namelist()
    print("total entries:",len(names))
    print("sha256:",hashlib.sha256(open(Z,"rb").read()).hexdigest())
    print("size:",os.path.getsize(Z))
    print()
    top={}
    for n in names:
        p=n.split("/")
        key = p[1] if p[0].startswith("CODOL-DEMONWARE-EVIDENCE-BUNDLE") and len(p)>1 else p[0]
        top[key]=top.get(key,0)+1
    for k in sorted(top): print("  %-52s %d"%(k,top[k]))
    print()
    print("root files:")
    for n in sorted(names):
        if n.count("/")==1: print("  ",n.split("/")[-1])
