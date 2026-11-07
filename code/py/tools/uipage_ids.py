#!/usr/bin/env python3
"""124 卷遗留: UIPage pageId(2..154, 28 种) → 页面名 映射.
   在 E 镜像里找 UI/AS3 侧: 'UIPage' 相关串, 页面名串表, pageId 表.
   线索: 客户端 AS3 常见命名 LobbyPage / Page_xx / *_Page.as 之类.
"""
import re
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read(); N=len(d)
def allhits(pat,lim=12):
    out=[];i=0
    while True:
        p=d.find(pat,i)
        if p<0: break
        out.append(p);i=p+1
        if len(out)>=lim: break
    return out
print("=== 关键字命中 ===")
for w in [b"UIPage",b"LobbyPage",b"lobbyPage",b"Page_",b"_Page",b"PageName",b"pageName",
          b"MainMenu",b"Barracks",b"CreateClass",b"PlaylistSelect",b"FrontEnd"]:
    h=allhits(w,10)
    print("  %-16s %d  命中%s"%(w.decode(),len(h),["0x%X"%x for x in h[:8]] or "—"))

# UIPage 上下文
print("\n=== 'UIPage' 上下文 (前3) ===")
for p in allhits(b"UIPage",3):
    lo=max(0,p-64);hi=min(N,p+96)
    seg=d[lo:hi]
    print("  @0x%X: %r"%(p,seg))
    print("     ascii: %r"%seg.decode("latin1","replace"))
