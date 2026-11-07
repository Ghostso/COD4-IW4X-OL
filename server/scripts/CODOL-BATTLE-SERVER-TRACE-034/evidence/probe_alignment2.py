import re, random
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
src=open(r"D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\references\client_probe\CodolNetchanTrace.py",encoding="utf-8",errors="replace").read()
rv=[(m.group(1),int(m.group(2),16)) for m in re.finditer(r"const\s+(\w+)\s*=\s*module\.base\.add\(0x([0-9A-Fa-f]+)\)", src)]
def pro(off):
    if off<0 or off+4>len(d): return False
    b=d[off:off+4]
    return b[:3] in (b"\x55\x8b\xec",b"\x6a\xff") or b[:2] in (b"\x8b\xff",b"\x55\x8b") or b[:1]==b"\x55"
for name,shift in [("offset = RVA",0),("offset = RVA + 0x400000",0x400000)]:
    hit=sum(1 for _,v in rv if pro(v+shift))
    print("%-28s -> prologue hits %d/%d" % (name,hit,len(rv)))
random.seed(1)
lo,hi=0x1000,0x8A6000
print("baseline random 48 in .text: %d" % sum(1 for _ in range(48) if pro(random.randrange(lo,hi))))
print()
print("=== Try known-SUCCESSFUL probe anchors from TASK-031 ===")
# TASK-031 proved: mmbook accepted string at VA 0xDC69B0 (offset 0x9C69B0);
# and parse/accepted handler 0x632680 landed as a real function with prologue.
import struct
for label, va in [("accepted parser (T-031, worked)",0x632680),("mmstart ctor (T-031, worked)",0x632070)]:
    off=va-0x400000
    print("  %-34s VA=%08X  file[VA-0x400000]=%s  file[VA]=%s" % (label,va,
        d[off:off+6].hex(), (d[va:va+6].hex() if va<len(d) else "OOR")))
