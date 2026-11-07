# -*- coding: utf-8 -*-
"""Phase A: inventory 040/041/042 files, verify internal manifests (read-only)."""
import sys, os, io, hashlib, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C

WS = C.WS
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

PROJ = ["CODOL-BATTLE-SERVER-DLL-NETBIND-040",
        "CODOL-BATTLE-SERVER-DLL-RECVBUFFER-TO-PARSER-041",
        "CODOL-BATTLE-SERVER-CLIENT-GAME-MSG-ENTRY-042"]

inv=[]
for proj in PROJ:
    base=os.path.join(WS,proj)
    for b,dirs,names in os.walk(base):
        dirs[:] = [d for d in dirs if d!='__pycache__']
        for n in names:
            p=os.path.join(b,n)
            rel=os.path.relpath(p,WS).replace('\\','/')
            inv.append((proj, rel, os.path.getsize(p), sha(p)))
inv.sort()
with io.open(os.path.join(C.EV,"inventory_040_041_042.tsv"),"w",encoding="utf-8",newline="") as f:
    f.write("PROJECT\tREL_PATH\tBYTES\tSHA256\n")
    for r in inv: f.write("%s\t%s\t%d\t%s\n"%r)
print("inventory rows:", len(inv))

# verify each project's SHA256SUMS.txt against actual files
for proj in PROJ:
    base=os.path.join(WS,proj); sums=os.path.join(base,"SHA256SUMS.txt")
    if not os.path.isfile(sums): print(proj,"NO SHA256SUMS"); continue
    ok=fail=missing=0; bad=[]
    for line in io.open(sums,encoding="utf-8"):
        line=line.rstrip("\n")
        if not line.strip(): continue
        try: h,rest=line.split("  *",1)
        except ValueError: 
            try: h,rest=line.split("  ",1)
            except ValueError: continue
        p=os.path.join(base,rest.replace("/",os.sep))
        if not os.path.isfile(p): missing+=1; bad.append(("MISSING",rest)); continue
        if sha(p)==h: ok+=1
        else: fail+=1; bad.append(("MISMATCH",rest))
    print("%-52s ok=%d fail=%d missing=%d" % (proj, ok, fail, missing))
    for kind,rest in bad[:15]: print("    ",kind,rest)
