IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
anch=[0x67520,0x1A5960,0x6BF80,0x6E6A0,0x6DEA0,0x6DB20,0x6D170,0x6C2F0,0x6CC60,0x6C840,
      0x6D060,0x1A4230,0x1A27F0,0x1A3670,0x1A3250,0x1A13A0,0x6E06B,0x6DAA0]
def pro(off):
    if off<0 or off+4>len(d): return False
    b=d[off:off+4]
    return b[:3] in (b"\x55\x8b\xec",b"\x6a\xff") or b[:2] in (b"\x8b\xff",b"\x55\x8b") or b[:1]==b"\x55"
print("Constant-delta hypothesis: does (probeRVA + D) land on prologues for many anchors?")
best=(0,0)
for D in range(-0x200000,0x200001,0x10):
    n=sum(1 for a in anch if pro(a+D))
    if n>best[1]: best=(D,n)
print("  best delta scanned (step 0x10): D=0x%X -> %d/%d hits" % (best[0]&0xffffffff,best[1],len(anch)))
# fine scan around best
D=best[0]
best2=(D,0)
for dd in range(D-0x20,D+0x21):
    n=sum(1 for a in anch if pro(a+dd))
    if n>best2[1]: best2=(dd,n)
print("  refined: D=0x%X -> %d/%d" % (best2[0]&0xffffffff,best2[1],len(anch)))
print()
print("Interpretation: if no D gives most anchors, the layouts are not a simple constant shift.")
print("Image sizes: local image_best=0x%X ; ol-mod out.exe (per 009 V-13)=0xE5D6000 ; local EXE=0xE659000" % 0xE659000)
print("  difference(local EXE - olmod out.exe) = 0x%X" % (0xE659000-0xE5D6000))
