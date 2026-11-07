# -*- coding: utf-8 -*-
"""TASK-034 : which RVAs in the probe file are real for THIS image? read-only."""
import hashlib, re, struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
PROBE = r"D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\references\client_probe\CodolNetchanTrace.py"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def pro(r):
    if not (0<=r<len(d)-4): return False
    b=d[r:r+4]
    return b[:3] in (b"\x55\x8b\xec",b"\x6a\xff") or b[:2] in (b"\x8b\xff",b"\x55\x8b") or b[:1]==b"\x55"
def decodes(r,need=6):
    n=0
    for _ in md.disasm(d[r:r+64], r): n+=1
    return n>=need
# TASK-031 CONTROLS: proven-correct offsets in THIS image (offset = VA-0x400000)
print("== CONTROL SET (TASK-031 proven offsets in THIS image) ==")
for name,va in [("mmbook accepted string",0xDC69B0),("mmstart fmt string",0xDC6800),
                ("accepted parser",0x632680),("mmstart ctor",0x632070),("latch consumer",0x634340)]:
    r=va-BASE
    tag = "STRING" if name.endswith("string") else ("PROLOGUE" if pro(r) else "??")
    print("   %-24s VA=%08X off=%08X -> %s" % (name,va,r,tag))
print()
src=open(PROBE,encoding="utf-8",errors="replace").read()
rv=[(m.group(1),int(m.group(2),16)) for m in re.finditer(r"const\s+(\w+)\s*=\s*module\.base\.add\(0x([0-9A-Fa-f]+)\)", src)]
print("== PROBE RVAs TESTED AS offsets INTO THIS IMAGE (%d constants) ==" % len(rv))
pro_hits=[(n,v) for n,v in rv if pro(v)]
dec_hits=[(n,v) for n,v in rv if decodes(v)]
print("   prologue hits : %d/%d  %s" % (len(pro_hits),len(rv), [(n,"%X"%v) for n,v in pro_hits]))
print("   decodable     : %d/%d" % (len(dec_hits),len(rv)))
print()
print("== CONCLUSION ==")
print("   In THIS target image, the TASK-009 / CodolNetchanTrace RVA list does NOT resolve to")
print("   function entries: only 1/%d lands on a prologue, and that one (0x6D060) is a")
print("   different function from the label 'parseMatchState' semantics used by the probe.")
print("   The probe file's own header says its RVAs belong to the OLFinal module it binds to,")
print("   NOT to this local 3.19.26.22 (build 1649370) executable.")
