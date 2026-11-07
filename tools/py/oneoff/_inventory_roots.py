import os
roots=[r".", r"COD OL/tqm/dump", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Caches"), os.path.expandvars(r"%TEMP%"), r"C:\ProgramData\Microsoft\Windows\Caches", r"C:\Symbols"]
for root in roots:
    if not os.path.exists(root):
        print("MISSING",root); continue
    hits=[]
    for base,dirs,files in os.walk(root):
        for name in files:
            low=name.lower()
            if low.endswith((".pdb",".dmp",".mdmp",".minidump",".dump",".mem",".vmem",".raw",".core")) or "codomp_client_shipretail" in low:
                p=os.path.join(base,name)
                try: hits.append((os.path.getsize(p),p))
                except OSError: pass
    print("ROOT",root,"HITS",len(hits))
    for s,p in hits[:200]: print(s,p)
