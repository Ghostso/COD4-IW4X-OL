# -*- coding: utf-8 -*-
"""Identity audit: enumerate all image_best.bin copies + recoverable client EXE/DLL
artifacts; hash them; classify by PE-ness and entry/section signature. Read-only."""
import sys, os, io, hashlib, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
import pefile

WS=C.WS
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

rows=[]
# all image_best.bin anywhere
for p in glob.glob(os.path.join(WS,"**","image_best.bin"), recursive=True):
    try: sz=os.path.getsize(p)
    except: continue
    try:
        pe=pefile.PE(p, fast_load=True)
        ib=hex(pe.OPTIONAL_HEADER.ImageBase); ep=hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)
        nsec=pe.FILE_HEADER.NumberOfSections
        sig="PE ib=%s ep=%s nsec=%d"%(ib,ep,nsec)
    except Exception as e:
        b=open(p,'rb').read(64)
        sig="NOT-PE head=%s"%b[:8].hex()
    rows.append((p,sz,sha(p),sig))
rows.sort()
with io.open(os.path.join(C.EV,"image_best_copies.tsv"),"w",encoding="utf-8",newline="") as f:
    f.write("PATH\tBYTES\tSHA256\tSIGNATURE\n")
    for r in rows: f.write("%s\t%d\t%s\t%s\n"%r)
print("image_best.bin copies:", len(rows))
seen={}
for p,sz,h,sig in rows:
    base=os.path.basename(os.path.dirname(p))
    key=(h,sz)
    seen.setdefault(key,[]).append(p)
for (h,sz),ps in sorted(seen.items(), key=lambda kv:-kv[0][1]):
    print("  sz=%d sha=%s x%d : %s" % (sz, h[:16], len(ps), ps[0]))
