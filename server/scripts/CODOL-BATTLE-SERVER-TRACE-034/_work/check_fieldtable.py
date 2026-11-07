import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def off(va): return va-BASE
def u32(va): return struct.unpack_from("<I",d,off(va))[0]
def cstr(va, n=40):
    o=off(va)
    if not (0<=o<len(d)): return "<OOR>"
    e=d.find(b"\x00",o); return d[o:e][:n]

RVA=0x855F70
for convention,va in [("VA = RVA + 0x400000 = %08X"%(BASE+RVA), BASE+RVA), ("VA = RVA = %08X"%RVA, RVA)]:
    print("=== %s ===" % convention)
    try:
        print("   first record raw:", d[off(va):off(va)+12].hex())
        name_ptr, f2, f3 = struct.unpack_from("<III", d, off(va))
        print("   rec0: name_ptr=%08X  f2=%d  f3=%d   name=%r" % (name_ptr,f2,f3,cstr(name_ptr)))
        for i in (0,1,2,234):
            np,f2,f3=struct.unpack_from("<III", d, off(va)+i*12)
            print("   rec[%3d]: name=%08X(%r)  +0x%X  bits=%d" % (i,np,cstr(np,28),f2,f3))
    except Exception as e:
        print("   ERR", e)
    print()
