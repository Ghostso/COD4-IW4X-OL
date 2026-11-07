import os, hashlib
WANT="07642387e67016546a0a1bab53522fe29becf2990740ccaa55e37c8fdfa2115a"
roots=[r"D:\BaiduNetdiskDownload\使命召唤OL", r"C:\Windows\System32\drivers\etc", r"C:\Temp",
       r"C:\Users\Z7-CT5N1\AppData\Local\Temp", r"C:\Users\Z7-CT5N1\AppData\Roaming"]
seen=0; hits=[]; sizes={}
for root in roots:
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames if d not in ('$Recycle.Bin','$Extend','node_modules','.git')]
        for fn in filenames:
            if not (fn.lower().startswith('hosts') or fn.lower().endswith(('.bak','.snapshot','.txt'))): 
                pass
            fp=os.path.join(dirpath,fn)
            try:
                sz=os.path.getsize(fp)
            except OSError: continue
            if sz!=937: continue
            seen+=1
            try: h=hashlib.sha256(open(fp,'rb').read()).hexdigest()
            except OSError: continue
            sizes[sz]=sizes.get(sz,0)+1
            if h==WANT: hits.append(fp)
print("937-byte files examined:",seen)
print("exact matches:",hits)
