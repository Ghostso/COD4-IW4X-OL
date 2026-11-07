# -*- coding: utf-8 -*-
import os, hashlib, collections
from pathlib import Path
ROOTS=[r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697"]
out=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_data\inventory.txt","w",encoding="utf-8")
ext=collections.Counter(); per_dir=collections.Counter()
pe_files=[]; total=0; nfiles=0
for root in ROOTS:
    for dp,dn,fn in os.walk(root):
        rel=os.path.relpath(dp,root)
        top=rel.split(os.sep)[0]
        for f in fn:
            p=os.path.join(dp,f); nfiles+=1
            try: sz=os.path.getsize(p)
            except: sz=-1
            total+=sz
            e=os.path.splitext(f)[1].lower(); ext[e]+=1
            per_dir[top]+=1
            # detect PE by MZ
            if sz>64:
                try:
                    with open(p,'rb') as fh:
                        hdr=fh.read(2)
                    if hdr==b'MZ': pe_files.append((sz,p))
                except: pass
out.write("total files: %d  total bytes: %d (%.1f MB)\n"%(nfiles,total,total/1048576))
out.write("\n== by extension ==\n")
for e,c in ext.most_common(60): out.write("  %-12s %d\n"%(e or '(none)',c))
out.write("\n== by top-level dir ==\n")
for d,c in per_dir.most_common(40): out.write("  %-28s %d\n"%(d,c))
out.write("\n== PE files (MZ) : %d ==\n"%len(pe_files))
for sz,p in sorted(pe_files, key=lambda x:-x[0])[:80]:
    out.write("  %10d  %s\n"%(sz,p))
out.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_data\inventory.txt",encoding="utf-8").read()[:6000])
