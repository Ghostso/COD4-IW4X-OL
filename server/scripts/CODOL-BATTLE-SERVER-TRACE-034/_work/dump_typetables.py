import struct, collections
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def b(va,n): return d[va-BASE:va-BASE+n]
T1=0x460550; n1=0x13A
T2=0x4606E4; n2=0x88
t1=b(T1,n1); t2=b(T2,n2)
print("=== type table A @%08X (index range 0..0x139 = %d entries) ===" % (T1,n1))
print("  distinct handler indices:", sorted(set(t1)))
print("  histogram:", dict(sorted(collections.Counter(t1).items())))
print("  full byte sequence:")
for r in range(0,n1,32):
    print("    +0x%03X: %s" % (r, " ".join("%02x"%x for x in t1[r:r+32])))
print()
print("=== type table B @%08X (index range 0..0x87 = %d entries) ===" % (T2,n2))
print("  distinct handler indices:", sorted(set(t2)))
print("  histogram:", dict(sorted(collections.Counter(t2).items())))
print("  full byte sequence:")
for r in range(0,n2,32):
    print("    +0x%03X: %s" % (r, " ".join("%02x"%x for x in t2[r:r+32])))
