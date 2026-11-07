"""Patch sandbox GDPLoader.dll: redirect discovery host to 127.0.0.1 (with backup)."""
import os, shutil, hashlib, sys, time, json

HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
SB=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923")
DLL=os.path.join(SB,"GDPLoader.dll")
BK=os.path.join(ROOT,"backups","GDP_PATCH_"+time.strftime("%Y%m%d_%H%M%S"))
os.makedirs(BK, exist_ok=True)

def sha(p):
    return hashlib.sha256(open(p,"rb").read()).hexdigest()

if not os.path.isfile(DLL):
    print("NO_DLL"); sys.exit(1)

shutil.copy2(DLL, os.path.join(BK,"GDPLoader.dll.orig"))
print("backup ->", os.path.join(BK,"GDPLoader.dll.orig"))

d = bytearray(open(DLL,"rb").read())
orig = bytes(d)

PATCHES = [
    (b"tqos.gamesafe.qq.com", b"127.0.0.1\x00"),
    (b"183.60.58.99",         b"127.0.0.1\x00"),
]
rep = []
for old, new in PATCHES:
    idx = 0
    n = 0
    while True:
        i = d.find(old, idx)
        if i < 0: break
        pad = old[len(new):]
        d[i:i+len(old)] = new + b"\x00"*len(pad)
        n += 1; idx = i+1
    rep.append({"old":old.decode(),"new":new.decode(),"count":n})
    print("patched %-24s -> %-12s x%d"%(old.decode(), new.decode(), n))

open(DLL,"wb").write(bytes(d))
print("sha before:", sha(os.path.join(BK,"GDPLoader.dll.orig"))[:16])
print("sha after :", sha(DLL)[:16])
json.dump({"backup":BK,"patches":rep}, open(os.path.join(BK,"patch.json"),"w"), indent=1)

# verify strings gone
chk = open(DLL,"rb").read()
for old,_ in PATCHES:
    print("  remaining %-24s : %d"%(old.decode(), chk.count(old)))
print("DONE")
