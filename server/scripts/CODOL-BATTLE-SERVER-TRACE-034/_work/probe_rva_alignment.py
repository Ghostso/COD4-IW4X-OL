import re, random
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
src=open(r"D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\references\client_probe\CodolNetchanTrace.py",encoding="utf-8",errors="replace").read()
# collect module.base.add(0x....) constants
rv=[(m.group(1),int(m.group(2),16)) for m in re.finditer(r"const\s+(\w+)\s*=\s*module\.base\.add\(0x([0-9A-Fa-f]+)\)", src)]
print("probe RVA constants found:", len(rv))
def is_prolog(off):
    if off<0 or off+2>len(d): return False
    b=d[off:off+4]
    return b[:3] in (b"\x55\x8b\xec", b"\x6a\xff") or b[:2] in (b"\x8b\xff", b"\x55\x8b") or b[:1]==b"\x55"
hit=[(n,v) for n,v in rv if is_prolog(v)]
print("landing on a prologue at offset==RVA : %d / %d" % (len(hit),len(rv)))
print("  hits:", ", ".join("%s(0x%X)"%(n,v) for n,v in hit) or "-")
miss=[(n,v) for n,v in rv if not is_prolog(v)]
print("  misses (%d)" % len(miss))
# baseline: random offsets in .text
random.seed(1234)
lo,hi=0x1000,0x8A6000
base=sum(1 for _ in range(len(rv)) if is_prolog(random.randrange(lo,hi)))
print("baseline: random %d samples in .text landed on prologue: %d" % (len(rv),base))
print()
print("Byte at each miss (first 6):")
for n,v in miss[:40]:
    print("  %-28s rva=0x%-8X -> %s" % (n,v,d[v:v+6].hex()))
