import os, re
targets=[b"ace-ats32", b"ACE-DRV32", b"ace-ats64", b"ACE-ATS64", b"ACE-DRV64", b"AntiCheatExpert", b"SGuard", b"ACE-BASE", b"ACE-GAME", b"ACE-SSC"]
roots=[r"COD OL", r"COD OL\TCLS", r"COD OL\tqm", r"COD OL\TGuard", r"COD OL\TCLS\TenProtect"]
hits={}
for r in roots:
    if not os.path.isdir(r): continue
    for dp,_,fns in os.walk(r):
        for fn in fns:
            if not fn.lower().endswith((".exe",".dll",".dat",".ini",".cfg",".txt")): continue
            p=os.path.join(dp,fn)
            try: d=open(p,"rb").read()
            except: continue
            for t in targets:
                if t in d or t.lower() in d.lower():
                    hits.setdefault(p,set()).add(t.decode())
for p,ts in sorted(hits.items()):
    print("%-70s %s"%(p, sorted(ts)))
