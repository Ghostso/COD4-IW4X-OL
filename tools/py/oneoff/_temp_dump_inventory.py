import os, struct, glob, time
roots=[os.path.expandvars(r"%TEMP%"), os.path.expandvars(r"%LOCALAPPDATA%\Temp")]
seen=set(); files=[]
for root in roots:
    if not os.path.exists(root): continue
    for base,dirs,names in os.walk(root):
        for name in names:
            low=name.lower()
            if low.endswith(('.dmp','.mdmp','.minidump')):
                p=os.path.join(base,name)
                if p.lower() in seen: continue
                seen.add(p.lower())
                try: files.append((os.path.getsize(p),p))
                except OSError: pass
for size,p in sorted(files, reverse=True):
    with open(p,'rb') as f: head=f.read(64)
    print(f'{size:12d} {head[:16].hex()} {head[:4]!r:8} {p}')
