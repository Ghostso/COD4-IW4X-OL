#!/usr/bin/env python3
"""在 E 镜像搜 dvar 名字串 '2486'/'3265' 等 (null-terminated), 看是否在 dvar 名表里。"""
import os
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read(); N=len(d)
for name in ["2486","2489","2574","2500","3265","2810"]:
    pat=name.encode()+b"\x00"
    i=0;hits=[]
    while True:
        p=d.find(pat,i)
        if p<0: break
        hits.append(p); i=p+1
        if len(hits)>=10: break
    print("%-6s null-str hits=%d %s"%(name,len(hits),["0x%X"%h for h in hits[:10]]))
    # 看上下文 (是否 dvar 名表: 周围都是短名)
    for h in hits[:2]:
        lo=max(0,h-40);hi=min(N,h+40)
        ctx=d[lo:hi]
        print("    @0x%X: %r"%(h, ctx))
