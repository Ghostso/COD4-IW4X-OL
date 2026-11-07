import os
def stat(root):
    tot=0; ph=0; sizes={}
    for dp,dn,fn in os.walk(root):
        for f in fn:
            if not f.lower().endswith(".png"): continue
            p=os.path.join(dp,f); s=os.path.getsize(p); tot+=1
            if s==69: ph+=1
            sizes[s]=sizes.get(s,0)+1
    return tot,ph,sizes
for label,root in [("沙箱",r"run_codol_001\sandbox_ifs1_20260923\IIPS\TPFUI\IIPSRes"),
                   ("原始",r"COD OL\IIPS\TPFUI\IIPSRes")]:
    tot,ph,sizes=stat(root)
    print("=== %s  %s"%(label,root))
    print("    png 总数=%d  69字节占位=%d"%(tot,ph))
    print("    大小分布(前8):", sorted(sizes.items())[:8])
