# -*- coding: utf-8 -*-
import os, hashlib, json
from pathlib import Path
ROOT=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697"
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_data")
rows=[]
for dp,dn,fn in os.walk(ROOT):
    for f in fn:
        p=os.path.join(dp,f); rel=os.path.relpath(p,ROOT)
        try: sz=os.path.getsize(p)
        except: sz=-1
        rows.append((rel,sz))
rows.sort()
with open(OUT/"file_list.txt","w",encoding="utf-8") as fh:
    for rel,sz in rows: fh.write("%10d  %s\n"%(sz,rel))
# hash the 4 PE modules + top-level py/json/script
mods=[r"native\bin2697\codol_dedrun.exe","client_room2697.dll","client_native_loopback.dll","client_loopback_guard.exe"]
with open(OUT/"module_hashes.txt","w",encoding="utf-8") as fh:
    for m in mods:
        p=os.path.join(ROOT,m)
        d=open(p,'rb').read()
        fh.write("%s  %d  %s\n"%(hashlib.sha256(d).hexdigest(),len(d),m))
print("files:",len(rows))
print(open(OUT/"module_hashes.txt",encoding="utf-8").read())
