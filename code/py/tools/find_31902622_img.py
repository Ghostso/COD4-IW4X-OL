#!/usr/bin/env python3
"""在 E 镜像/Base.dll/EXE 搜 31902622 (0x01E6CB9E) 立即数, 及 16 字节会话串 nQloP0oCVWR6RDJS。"""
import os, struct
V=31902622
PAT_V=struct.pack("<I",V)
PAT_V_BE=struct.pack(">I",V)
SESS=b"nQloP0oCVWR6RDJS"
PATHS=[(r"E:\codol_re\client_image_20261027.bin","E_image"),
       (r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll","Base.dll"),
       (r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe","EXE")]
for path,lab in PATHS:
    if not os.path.exists(path): print("[%s] MISSING"%lab); continue
    d=open(path,"rb").read()
    print("=== [%s] size=0x%X ==="%(lab,len(d)))
    for name,pat in [("V_LE",PAT_V),("V_BE",PAT_V_BE),("SESS",SESS)]:
        i=0;hits=[]
        while True:
            p=d.find(pat,i)
            if p<0: break
            hits.append(p); i=p+1
            if len(hits)>=10: break
        print("  %-8s n=%d %s"%(name,len(hits),["0x%X"%h for h in hits[:10]]))
