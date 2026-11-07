import os
root=r"D:\BaiduNetdiskDownload\使命召唤OL"
skip=("\\REF_LOBBY_KIT\\","__pycache__","\\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\\","\\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\\")
exts={".md",".txt",".py",".cpp",".hpp",".h",".c",".cs",".json",".csv",".log"}
hits=[]
for dp,dn,fn in os.walk(root):
    if any(x in dp for x in skip): continue
    for f in fn:
        if os.path.splitext(f)[1].lower() not in exts: continue
        p=os.path.join(dp,f)
        try:
            if os.path.getsize(p)>20_000_000: continue
            b=open(p,"rb").read()
        except Exception: continue
        for pat in (b"CLIENTCHAL",b"BDDATA"):
            if pat in b:
                hits.append((pat.decode(),p)); break
for t,p in hits: print(t,p)
print("TOTAL",len(hits))
